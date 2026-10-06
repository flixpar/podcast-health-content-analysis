"""Episodes whose audio files follow a dated naming scheme on a public host.

Some hosts keep every file a show ever published at a predictable URL, long
after the feed stopped listing it: The Dave Ramsey Show on Libsyn
(``traffic.libsyn.com/secure/daveramseycf/MMDDYYYY_N_the_dave_ramsey_show.mp3``,
three hour-long parts a weekday) is the case this was written for. For each day
in a podcast's chosen study windows, and each part ``N`` from 1, the file is
probed with a small ranged GET until a part is missing. A probed file counts
only if it is audio and its own ID3 title carries the date it was guessed for
(``--id3-date-format``), so a wrong guess can never be recorded as an episode.

Writes ``import-episodes`` JSONL; nothing is written to the database. Titles
are the ID3 title plus the part (the feed gave all three parts of a day the
same title, which ``import-episodes`` would merge as one episode).

    ../.venv/bin/python tools/alternate_sources/file_pattern.py apple-top24-monthly OUT_DIR 73 \\
        --template 'https://traffic.libsyn.com/secure/daveramseycf/{date:%m%d%Y}_{n}_the_dave_ramsey_show.mp3' \\
        --id3-date-format '%m/%d/%Y' --windows 2019-11 2019-12 2020-01
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.alternate_sources.common import Fetcher, open_db, range_probe, write_jsonl  # noqa: E402

SOURCE = "host_file_pattern"
MAX_PARTS = 6


def window_days(conn, study: str, podcast_id: int, labels: list[str]) -> list[tuple[str, date]]:
    rows = conn.execute("""
        SELECT w.label, w.start_date, w.end_date FROM study_windows w
        JOIN study_members m ON m.study = w.study AND m.entity = w.entity
        WHERE w.study = ? AND m.podcast_id = ? ORDER BY w.start_date
    """, (study, podcast_id)).fetchall()
    out = []
    for r in rows:
        if labels and r["label"] not in labels:
            continue
        d, end = date.fromisoformat(r["start_date"]), date.fromisoformat(r["end_date"])
        while d < end:
            out.append((r["label"], d))
            d += timedelta(days=1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("study")
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("podcast_id", type=int)
    ap.add_argument("--template", required=True, help="URL with {date:<strftime>} and {n}")
    ap.add_argument("--id3-date-format", required=True,
                    help="how the date appears in the file's ID3 title (strftime)")
    ap.add_argument("--windows", nargs="*", default=[], help="window labels (default: all)")
    ap.add_argument("--hour", default=12, type=int, help="UTC hour to give the publication time")
    args = ap.parse_args()

    conn = open_db()
    days = window_days(conn, args.study, args.podcast_id, args.windows)
    conn.close()
    fetcher = Fetcher()
    rows, misses = [], []
    for label, day in days:
        for n in range(1, MAX_PARTS + 1):
            url = args.template.format(date=day, n=n)
            probe = range_probe(fetcher, url)
            if not probe.is_audio:
                if n == 1:
                    misses.append(day.isoformat())
                break
            stamp = day.strftime(args.id3_date_format)
            if not probe.id3_title or stamp not in probe.id3_title:
                print(f"  {url}: ID3 title {probe.id3_title!r} lacks {stamp}; not recorded", flush=True)
                break
            rows.append({
                "podcast_id": args.podcast_id, "title": f"{probe.id3_title} (part {n})",
                "published_date": f"{day.isoformat()}T{args.hour:02d}:00:00", "audio_url": url,
                "guid": f"{SOURCE}:{url.split('?')[0]}",
                "evidence": {"route": "dated file naming on the show's host, confirmed by the file's ID3 title",
                             "template": args.template, "window": label, "part": n,
                             "probe": {"is_audio": True, "status": probe.status,
                                       "total_size": probe.total_size, "id3_title": probe.id3_title,
                                       "estimated_seconds": (probe.duration or {}).get("seconds")}},
            })
            if probe.duration:
                rows[-1]["duration_seconds"] = round(probe.duration["seconds"])
        write_jsonl(args.out_dir / f"{SOURCE}.jsonl", rows)
    print(f"{len(rows)} files over {len(days)} days; no file on {len(misses)} days")


if __name__ == "__main__":
    main()
