#!/usr/bin/env python3
"""Keyword search over the flattened podcast transcript corpus.

Corpus: $CORPUS_TEXT_DIR/shard_NN.tsv (default local/corpus-text), one transcript segment
per line: `episode_id<TAB>segment_index<TAB>text`. Patterns use regex syntax
shared by Python and ripgrep, matched case-insensitively against segment text.

  cq.py count  'pattern'                  # segments, episodes, podcasts; top podcasts
  cq.py sample 'pattern' [-n 12] [--seed 1] [--ctx 1] [--podcast 'regex'] [--width 500]
  cq.py ctx EPISODE SEGMENT [-k 3]         # the segments around one hit
  cq.py cooc 'pattern A' 'pattern B'      # episodes matching both, with a sample
"""
import argparse
import json
import random
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import os

# Generated shards are ignored; CORPUS_TEXT_DIR can select an external volume.
REPO = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("CORPUS_TEXT_DIR", str(REPO / "local" / "corpus-text")))
_meta = None


def meta():
    global _meta
    if _meta is None:
        rows = {}
        with open(ROOT / "episodes.tsv", encoding="utf-8") as f:
            header = f.readline().rstrip("\n")
            if header != "episode_id\tpodcast_id\tpodcast\tdate\tepisode_title":
                raise CorpusQueryError("Invalid corpus metadata header; rebuild the corpus")
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) != 5:
                    raise CorpusQueryError("Malformed corpus metadata row; rebuild the corpus")
                rows[int(parts[0])] = (parts[2], parts[3], parts[4])
        _meta = rows
    return _meta


class CorpusQueryError(RuntimeError):
    pass


def corpus_files():
    """Reject failed builds and damaged corpora before returning search inputs."""
    manifest_path = ROOT / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, ValueError) as exc:
        raise CorpusQueryError(f"Cannot read completion manifest {manifest_path}; rebuild the corpus") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "corpus-text-v1":
        raise CorpusQueryError("Unsupported corpus manifest; rebuild the corpus")
    if manifest.get("complete") is not True:
        raise CorpusQueryError("Corpus build is incomplete; select a successfully published corpus")
    # v1 assigns episode IDs modulo 64, including context lookups below.
    if type(manifest.get("shards")) is not int or manifest["shards"] != 64:
        raise CorpusQueryError("Unsupported corpus shard count; corpus-text-v1 requires 64 shards")
    shards = [ROOT / f"shard_{i:02d}.tsv" for i in range(manifest["shards"])]
    missing = [path.name for path in [ROOT / "episodes.tsv", *shards] if not path.is_file()]
    if missing:
        raise CorpusQueryError(f"Incomplete corpus files in {ROOT}: {', '.join(missing)}; rebuild the corpus")
    return [str(path) for path in shards]


def matches(pattern, files=None):
    # ripgrep finds candidate lines fast; the text column is re-checked here so
    # a pattern can never match an episode id or segment number.
    files = corpus_files() if files is None else files
    if not files:
        raise CorpusQueryError(f"No corpus shards in {ROOT}; run corpus_text/build.py first")
    check = re.compile(pattern, re.I)
    # Anchor to segment text rather than its TSV episode ID. Expressions with
    # anchors bypass the prefilter and are checked against text below.
    prefilter = "." if "^" in pattern else pattern
    proc = subprocess.Popen(
        ["rg", "-i", "--no-filename", "--no-line-number", "-e", prefilter, *files],
        stdout=subprocess.PIPE, text=True, errors="replace",
    )
    try:
        for line in proc.stdout:
            parts = line.rstrip("\n").split("\t", 2)
            if len(parts) != 3:
                raise CorpusQueryError("Malformed corpus shard row; rebuild the corpus")
            if check.search(parts[2]):
                yield int(parts[0]), int(parts[1]), parts[2]
        if proc.wait() not in (0, 1):
            raise CorpusQueryError("ripgrep search failed; check the pattern and corpus paths")
    finally:
        proc.stdout.close()
        if proc.poll() is None:
            proc.terminate()
        proc.wait()


def snippet(text, pattern, width):
    m = re.search(pattern, text, re.I)
    if not m or len(text) <= width:
        return text[:width]
    start = max(0, m.start() - width // 2)
    return ("…" if start else "") + text[start:start + width] + ("…" if start + width < len(text) else "")


def segments(ep, lo, hi):
    corpus_files()
    shard = ROOT / f"shard_{ep % 64:02d}.tsv"
    result = subprocess.run(["rg", "--no-filename", "--no-line-number", f"^{ep}\t", str(shard)], capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise CorpusQueryError(f"Cannot read corpus shard {shard}: {result.stderr.strip()}")
    out = result.stdout
    rows = []
    for line in out.splitlines():
        e, s, t = line.split("\t", 2)
        if lo <= int(s) <= hi:
            rows.append((int(s), t))
    return sorted(rows)


def cmd_count(a):
    segs = 0
    eps, pods = Counter(), Counter()
    m = meta()
    for ep, _, _ in matches(a.pattern):
        segs += 1
        eps[ep] += 1
    for ep, n in eps.items():
        pods[m.get(ep, ("?",))[0]] += 1
    print(f"segments {segs}  episodes {len(eps)}  podcasts {len(pods)}")
    for name, n in pods.most_common(a.top):
        print(f"  {n:6d} eps  {name}")


def cmd_sample(a):
    rng = random.Random(a.seed)
    m = meta()
    pod = re.compile(a.podcast, re.I) if a.podcast else None
    reservoir, seen = [], 0
    for hit in matches(a.pattern):
        if pod and not pod.search(m.get(hit[0], ("",))[0]):
            continue
        seen += 1
        if len(reservoir) < a.n:
            reservoir.append(hit)
        else:
            j = rng.randrange(seen)
            if j < a.n:
                reservoir[j] = hit
    print(f"{seen} matching segments; showing {len(reservoir)}\n")
    for ep, seg, text in reservoir:
        name, date, title = m.get(ep, ("?", "?", "?"))
        print(f"## ep {ep} seg {seg} | {name} | {date} | {title[:80]}")
        if a.ctx:
            for s, t in segments(ep, seg - a.ctx, seg + a.ctx):
                mark = ">>" if s == seg else "  "
                print(f"{mark} [{s}] {snippet(t, a.pattern, a.width) if s == seg else t[: a.width]}")
        else:
            print("   " + snippet(text, a.pattern, a.width))
        print()


def cmd_ctx(a):
    m = meta()
    name, date, title = m.get(a.episode, ("?", "?", "?"))
    print(f"ep {a.episode} | {name} | {date} | {title}")
    for s, t in segments(a.episode, a.segment - a.k, a.segment + a.k):
        print(f"{'>>' if s == a.segment else '  '} [{s}] {t}")


def cmd_cooc(a):
    m = meta()
    first = {ep for ep, _, _ in matches(a.a)}
    both = {ep for ep, _, _ in matches(a.b) if ep in first}
    pods = Counter(m.get(ep, ("?",))[0] for ep in both)
    print(f"A: {len(first)} episodes; A and B: {len(both)} episodes")
    for name, n in pods.most_common(10):
        print(f"  {n:6d} eps  {name}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("count"); c.add_argument("pattern"); c.add_argument("--top", type=int, default=12); c.set_defaults(f=cmd_count)
    s = sub.add_parser("sample"); s.add_argument("pattern"); s.add_argument("-n", type=int, default=12); s.add_argument("--seed", type=int, default=1)
    s.add_argument("--ctx", type=int, default=0); s.add_argument("--podcast"); s.add_argument("--width", type=int, default=500); s.set_defaults(f=cmd_sample)
    x = sub.add_parser("ctx"); x.add_argument("episode", type=int); x.add_argument("segment", type=int); x.add_argument("-k", type=int, default=3); x.set_defaults(f=cmd_ctx)
    o = sub.add_parser("cooc"); o.add_argument("a"); o.add_argument("b"); o.set_defaults(f=cmd_cooc)
    a = p.parse_args()
    try:
        corpus_files()
        a.f(a)
    except (CorpusQueryError, OSError, ValueError, re.error) as exc:
        p.exit(2, f"corpus query: {exc}; see analysis/corpus_text/README.md\n")


if __name__ == "__main__":
    main()
