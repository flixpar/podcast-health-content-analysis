"""A keyword screen from the v8 corpus reviewers' own cq.py queries.

Union of every count/sample regex the topic and narrative reviewers (report
slices 01-13) ran over the corpus; a window's score is the number of its units
that match any of them. Patterns are run case-insensitively on raw unit text,
as cq.py (ripgrep -i) ran them.

    python exp/review_query_screen.py /scratch/.../v8-corpus-review-queries/cq_invocations.jsonl
"""
import json, re, sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from screens import write_scores

rows = [json.loads(l) for l in open(sys.argv[1])]
patterns = set()
for r in rows:
    if r.get("subcommand") in ("count", "sample") and r["slice"][:2] <= "13" and not r.get("unresolved_variable"):
        for p in r.get("patterns") or []:
            try:
                re.compile(p, re.I)
                patterns.add(p)
            except re.error:
                pass
BIG = re.compile("|".join(f"(?:{p})" for p in sorted(patterns)), re.I)


def count(window):
    return window["window_id"], float(sum(1 for u in window["units"] if BIG.search(u["text"])))


if __name__ == "__main__":
    windows = [json.loads(l) for l in open("exp/corpus/screen-windows.jsonl")]
    with Pool(48) as pool:
        scores = dict(pool.imap_unordered(count, windows, chunksize=4))
    write_scores("kw-review-queries", scores)
    print(len(patterns), "patterns;", len(scores), "windows")
