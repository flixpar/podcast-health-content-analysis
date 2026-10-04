"""Flatten every transcript into 64 plain-text shards: one segment per line,
`episode_id<TAB>segment_index<TAB>text`, shard = episode_id % 64."""
import json, os, sqlite3, sys
from multiprocessing import Pool
from pathlib import Path
import zstandard

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "downloader/data/transcripts"
OUT = Path(os.environ.get("CORPUS_TEXT_DIR", "/mnt/internal/felix/podcast-corpus-text"))
N = 64

def work(shard):
    dctx = zstandard.ZstdDecompressor()
    lines = segs = eps = 0
    with open(OUT / f"shard_{shard:02d}.tsv", "w", encoding="utf-8") as out:
        for path in SRC.glob("episode_*.jsonl.zst"):
            ep = int(path.name[8:-10])
            if ep % N != shard:
                continue
            try:
                with open(path, "rb") as fh, dctx.stream_reader(fh) as reader:
                    data = reader.read().decode("utf-8", "replace")
            except Exception:
                continue
            eps += 1
            for raw in data.splitlines():
                try:
                    rec = json.loads(raw)
                except Exception:
                    continue
                if rec.get("type") != "segment":
                    continue
                text = " ".join(str(rec.get("text") or "").split())
                if text:
                    out.write(f"{ep}\t{rec.get('index')}\t{text}\n")
                    segs += 1
    return shard, eps, segs

if __name__ == "__main__":
    with Pool(28) as pool:
        total_e = total_s = 0
        for shard, e, s in pool.imap_unordered(work, range(N)):
            total_e += e; total_s += s
        print("episodes", total_e, "segments", total_s)
    con = sqlite3.connect(f"file:{REPO}/downloader/data/podcast_metadata.db?mode=ro", uri=True)
    with open(OUT / "episodes.tsv", "w", encoding="utf-8") as f:
        f.write("episode_id\tpodcast_id\tpodcast\tdate\tepisode_title\n")
        for row in con.execute("SELECT e.id, e.podcast_id, p.title, substr(e.published_date,1,10), e.title FROM episodes e JOIN podcasts p ON p.id=e.podcast_id"):
            f.write("\t".join(" ".join(str(x or "").split()) for x in row) + "\n")
