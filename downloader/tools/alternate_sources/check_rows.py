"""Last check on alternate-source JSONL before ``import-episodes``.

A row is held back when its evidence contradicts it:

* its probe found no audio (``probe.is_audio`` false) -- only for rows that
  *repair* an episode (``replaces_episode_id``): a new episode whose enclosure
  is dead now can still be fetched by ``download --wayback-fallback``;
* the audio's own ID3 title names another episode (word overlap with the
  row's title below ``MIN_TITLE_OVERLAP``);
* its estimated length does not fit the declared duration
  (``common.duration_matches``).

Writes ``<stem>.accepted.jsonl`` and ``<stem>.held.jsonl`` (with reasons) next
to the input, and prints a summary.

    ../.venv/bin/python tools/alternate_sources/check_rows.py OUT_DIR/wayback_prefix.jsonl
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.alternate_sources.common import read_jsonl, write_jsonl  # noqa: E402

MIN_TITLE_OVERLAP = 0.5
_STOP = {"the", "a", "an", "of", "and", "in", "on", "to", "for", "with", "is", "at", "by", "ep", "episode"}


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in _STOP}


def title_overlap(a: str, b: str) -> float:
    """Share of the shorter title's words found in the other."""
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return 1.0
    return len(wa & wb) / min(len(wa), len(wb))


def problems(row: dict) -> list[str]:
    probe = (row.get("evidence") or {}).get("probe")
    out = []
    if probe is None:
        return out
    if "is_audio" in probe and not probe["is_audio"] and "replaces_episode_id" in row:
        out.append(f"no audio at the new URL: {probe.get('error')}")
    id3 = probe.get("id3_title")
    if id3 and title_overlap(id3, row["title"]) < MIN_TITLE_OVERLAP:
        out.append(f"ID3 title {id3!r} does not match {row['title']!r}")
    est, declared = probe.get("estimated_seconds"), probe.get("declared_seconds")
    if est and declared and not 0.9 <= est / declared <= 1.35:
        out.append(f"length {est}s does not fit declared {declared}s")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jsonl", type=Path)
    args = ap.parse_args()
    rows = read_jsonl(args.jsonl)
    accepted, held = [], []
    for row in rows:
        why = problems(row)
        if why:
            held.append({**row, "held_because": why})
        else:
            accepted.append(row)
    stem = args.jsonl.with_suffix("")
    write_jsonl(stem.with_suffix(".accepted.jsonl"), accepted)
    write_jsonl(stem.with_suffix(".held.jsonl"), held)
    print(f"{len(rows)} rows: {len(accepted)} accepted, {len(held)} held")
    for h in held:
        print(f"  held: {h['title'][:60]}: {'; '.join(h['held_because'])}")


if __name__ == "__main__":
    main()
