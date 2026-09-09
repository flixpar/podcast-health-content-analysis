"""One-pass lexicon scan over every transcript.

Reads analysis/fast/lexicon.json, decompresses each transcript, splits it into
sentences, and records (a) per-episode counts of sentences matching every term
and label, and (b) every sentence that matched anything, with its position.
Runs on all cores; output is parquet under OUT_DIR.
"""
import io, json, os, re, sqlite3, sys, time
from collections import Counter
from multiprocessing import Pool

import pyarrow as pa
import pyarrow.parquet as pq
import zstandard as zstd

ROOT = "/home/felix/projects/podcast-misinfo"
DB = f"{ROOT}/downloader/data/podcast_metadata.db"
LEX = os.environ.get("SCAN_LEX", f"{ROOT}/analysis/fast/lexicon.json")
OUT_DIR = os.environ.get("SCAN_OUT", "/mnt/data2/podcast-data/fast-analysis/scan")

REGEX_CHARS = set("()|?[]\\+*{}")
SPEAKER_RE = re.compile(r"^\s*(?:Speaker\s*\d+|[A-Z][A-Za-z .'-]{1,40})\s*:\s+")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(\[])")


def trie_regex(words):
    """Compile a list of literal phrases into one trie-shaped alternation."""
    trie = {}
    for w in words:
        node = trie
        for ch in w:
            node = node.setdefault(ch, {})
        node[""] = True

    def build(node):
        if "" in node and len(node) == 1:
            return ""
        alts, chars = [], []
        for ch, sub in sorted(node.items()):
            if ch == "":
                continue
            r = build(sub)
            (chars if r == "" else alts).append(re.escape(ch) if r == "" else re.escape(ch) + r)
        if chars:
            alts.append(chars[0] if len(chars) == 1 else "[" + "".join(chars) + "]")
        out = alts[0] if len(alts) == 1 else "(?:" + "|".join(alts) + ")"
        return out + "?" if "" in node else out

    return build(trie)


class Matcher:
    def __init__(self, lex):
        # literal term -> list of (section, label); regex terms kept separately
        self.literal = {}
        self.regex = []  # (compiled, section, label, term)
        self.sections = {}
        for section, body in lex.items():
            if section in ("topics", "frames", "evidence", "narratives", "products", "certainty"):
                for label, spec in body.items():
                    for t in spec["terms"]:
                        self._add(t, section, label)
            else:  # commercial, distrust, correction: flat
                for t in body["terms"]:
                    self._add(t, section, section)
        words = sorted(self.literal)
        self.lit_re = re.compile(r"\b(?:" + trie_regex(words) + r")\b", re.I)

    def _add(self, term, section, label):
        term = term.strip().lower()
        if not term:
            return
        if any(c in REGEX_CHARS for c in term):
            self.regex.append((re.compile(term, re.I), section, label, term))
        else:
            self.literal.setdefault(term, []).append((section, label))

    def match(self, sentence):
        hits = []  # (section, label, term)
        low = sentence.lower()
        for m in self.lit_re.finditer(low):
            t = m.group(0)
            for sec, lab in self.literal.get(t, ()):
                hits.append((sec, lab, t))
        if hits:  # regex patterns (narratives) only on sentences that hit something
            for rx, sec, lab, term in self.regex:
                if rx.search(low):
                    hits.append((sec, lab, term))
        return hits


_M = None


def _init():
    global _M
    with open(LEX) as f:
        _M = Matcher(json.load(f))


def scan_one(job):
    episode_id, path = job
    try:
        with open(path, "rb") as f:
            raw = zstd.ZstdDecompressor().stream_reader(f).read()
    except Exception as e:  # noqa
        return episode_id, None, str(e)
    n_words = n_sent = n_seg = 0
    speaker_prefix = 0
    counts = Counter()      # (section,label,term) -> n sentences
    sents = []              # rows
    dur = 0.0
    src = ""
    for line in raw.decode("utf-8", "replace").splitlines():
        if not line:
            continue
        d = json.loads(line)
        t = d.get("type")
        if t == "metadata":
            src = d.get("source", "")
            continue
        if t != "segment":
            continue
        n_seg += 1
        text = d.get("text") or ""
        end = d.get("end")
        if end is not None:
            dur = max(dur, float(end))
        start = d.get("start")
        m = SPEAKER_RE.match(text)
        speaker = None
        if m:
            speaker_prefix += 1
            speaker = m.group(0).strip().rstrip(":").strip()
            text = text[m.end():]
        for s in SENT_SPLIT.split(text):
            s = s.strip()
            if not s:
                continue
            n_sent += 1
            n_words += s.count(" ") + 1
            hits = _M.match(s)
            if hits:
                seen = set()
                for h in hits:
                    if h not in seen:
                        seen.add(h)
                        counts[h] += 1
                labels = sorted({f"{sec}:{lab}" for sec, lab, _ in hits})
                sents.append((episode_id, n_seg - 1, start, n_sent - 1, speaker, "|".join(labels), s[:600]))
    meta = (episode_id, src, n_seg, n_sent, n_words, dur, speaker_prefix)
    crows = [(episode_id, sec, lab, term, n) for (sec, lab, term), n in counts.items()]
    return episode_id, (meta, crows, sents), None


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    os.makedirs(OUT_DIR, exist_ok=True)
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    jobs = conn.execute("select episode_id, file_path from transcripts order by episode_id").fetchall()
    if limit:
        import random
        random.seed(0)
        jobs = random.sample(jobs, limit)
    print(f"{len(jobs)} transcripts", flush=True)
    meta_schema = pa.schema([("episode_id", pa.int64()), ("source", pa.string()), ("n_seg", pa.int32()),
                             ("n_sent", pa.int32()), ("n_words", pa.int32()), ("duration", pa.float32()),
                             ("speaker_prefixed_segs", pa.int32())])
    cnt_schema = pa.schema([("episode_id", pa.int64()), ("section", pa.string()), ("label", pa.string()),
                            ("term", pa.string()), ("n_sent", pa.int32())])
    sent_schema = pa.schema([("episode_id", pa.int64()), ("seg", pa.int32()), ("start", pa.float32()),
                             ("sent_idx", pa.int32()), ("speaker", pa.string()), ("labels", pa.string()),
                             ("text", pa.string())])
    writers = {k: pq.ParquetWriter(f"{OUT_DIR}/{k}.parquet", s, compression="zstd")
               for k, s in (("episodes", meta_schema), ("counts", cnt_schema), ("sentences", sent_schema))}
    buf = {"episodes": [], "counts": [], "sentences": []}
    errors = []

    def flush():
        for k, w in writers.items():
            if buf[k]:
                cols = list(zip(*buf[k]))
                w.write_table(pa.table({n: list(c) for n, c in zip(w.schema.names, cols)}, schema=w.schema))
                buf[k] = []

    t0 = time.time()
    n = 0
    with Pool(int(os.environ.get("SCAN_PROCS", "28")), initializer=_init) as pool:
        for eid, res, err in pool.imap_unordered(scan_one, jobs, chunksize=8):
            n += 1
            if err:
                errors.append((eid, err))
                continue
            meta, crows, sents = res
            buf["episodes"].append(meta)
            buf["counts"].extend(crows)
            buf["sentences"].extend(sents)
            if len(buf["sentences"]) > 200_000 or len(buf["counts"]) > 1_000_000:
                flush()
            if n % 2000 == 0:
                print(f"{n}/{len(jobs)} {time.time()-t0:.0f}s", flush=True)
    flush()
    for w in writers.values():
        w.close()
    with open(f"{OUT_DIR}/errors.json", "w") as f:
        json.dump(errors, f)
    print(f"done {n} in {time.time()-t0:.0f}s, {len(errors)} errors", flush=True)


if __name__ == "__main__":
    main()
