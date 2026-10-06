"""Read-only audit: fully decode a stratified sample of a study's downloaded audio.

ffprobe's header duration is not evidence that a file is whole (a truncated
MP3 keeps the duration its header advertised), so every sampled file is
decoded from sample zero to the end. For each file the CSV records the header
duration, the decoded duration (16 kHz mono sample count from
``volumedetect``), the feed's declared ``duration_seconds``, decoder error
lines, mean/max volume, and flags:

* ``decode_errors``: the decoder logged errors (corrupt frames);
* ``truncated``: decoded < 90% of the declared duration (and > 60 s short);
* ``header_lies``: header duration > decoded by more than 5% and 30 s;
* ``longer_than_declared``: decoded > 125% of declared and > 120 s longer
  (often a different file than the one the feed describes);
* ``short_lt60``: decoded under 60 s; ``near_silent``: mean volume < -50 dB;
* ``not_audio``: no audio stream, or the file is missing.

Strata are the audio's provenance: ``wayback_audio`` and ``unwrapped_audio``
(from ``episode_sources``) and plain ``feed``. Files are only read.

    ../.venv/bin/python tools/audit/decode_sample.py apple-top24-monthly OUT.csv \
        --per-stratum feed=100 wayback_audio=0 unwrapped_audio=0   # 0 = all
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from podcast_pipeline import paths  # noqa: E402
from podcast_pipeline.config import DEFAULT_CONFIG_PATH, Config  # noqa: E402

RATE = 16000


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,format_name:stream=codec_type,codec_name",
         "-of", "json", str(path)], capture_output=True, text=True)
    if out.returncode != 0:
        return {"probe_error": out.stderr.strip()[:200]}
    j = json.loads(out.stdout)
    audio = [s for s in j.get("streams", []) if s.get("codec_type") == "audio"]
    return {"header_duration": float(j.get("format", {}).get("duration") or 0) or None,
            "format": j.get("format", {}).get("format_name"),
            "codec": audio[0]["codec_name"] if audio else None,
            "has_audio_stream": bool(audio)}


def decode(path: Path) -> dict:
    out = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-loglevel", "repeat+level+info", "-i", str(path),
         "-vn", "-af", f"aresample={RATE},aformat=channel_layouts=mono,volumedetect", "-f", "null", "-"],
        capture_output=True, text=True)
    lines = out.stderr.splitlines()
    errors = [l for l in lines if "[error]" in l or "[fatal]" in l]
    samples = [int(m.group(1)) for l in lines if (m := re.search(r"n_samples: (\d+)", l))]
    mean = [float(m.group(1)) for l in lines if (m := re.search(r"mean_volume: (-?[\d.]+|-inf) dB", l))
            if m.group(1) != "-inf"]
    mx = [float(m.group(1)) for l in lines if (m := re.search(r"max_volume: (-?[\d.]+) dB", l))]
    return {"returncode": out.returncode,
            "decoded_duration": round(max(samples) / RATE, 1) if samples else 0.0,
            "decode_error_lines": len(errors), "first_error": errors[0][:200] if errors else "",
            "mean_volume_db": mean[0] if mean else None, "max_volume_db": mx[0] if mx else None}


def check(row: dict, config: Config) -> dict:
    path = paths.resolve(config, row["audio_file_path"])
    rec = {**row, "local_path": str(path) if path else "", "exists": bool(path and path.exists())}
    if not rec["exists"]:
        rec["flags"] = "not_audio(missing)"
        return rec
    rec["size_mb"] = round(path.stat().st_size / 1e6, 2)
    rec.update(probe(path))
    rec.update(decode(path))
    dec, declared, header = rec.get("decoded_duration") or 0, row["duration_seconds"], rec.get("header_duration")
    flags = []
    if not rec.get("has_audio_stream"):
        flags.append("not_audio")
    if rec.get("decode_error_lines") or rec.get("returncode"):
        flags.append("decode_errors")
    if declared and declared > 0 and dec < 0.9 * declared and declared - dec > 60:
        flags.append("truncated")
    if header and header - dec > max(30, 0.05 * header):
        flags.append("header_lies")
    if declared and declared > 0 and dec > 1.25 * declared and dec - declared > 120:
        flags.append("longer_than_declared")
    if dec < 60:
        flags.append("short_lt60")
    if rec.get("mean_volume_db") is not None and rec["mean_volume_db"] < -50:
        flags.append("near_silent")
    rec["flags"] = ";".join(flags)
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("study")
    ap.add_argument("out")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    ap.add_argument("--per-stratum", nargs="+", default=["feed=100", "wayback_audio=0", "unwrapped_audio=0"])
    ap.add_argument("--seed", type=int, default=20261003)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    config = Config.load(args.config)
    conn = sqlite3.connect(f"file:{config.db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("""
        SELECT e.id AS episode_id, e.podcast_id, s.window_label, e.title, e.published_date,
               e.duration_seconds, e.audio_file_path,
               COALESCE((SELECT MIN(x.source) FROM episode_sources x WHERE x.episode_id = e.id
                         AND x.source IN ('wayback_audio', 'unwrapped_audio')), 'feed') AS stratum
        FROM study_episodes s JOIN episodes e ON e.id = s.episode_id
        WHERE s.study = ? AND e.status = 'downloaded' AND e.audio_file_path IS NOT NULL
        ORDER BY e.id
    """, (args.study,))]
    rng = random.Random(args.seed)
    sample = []
    for spec in args.per_stratum:
        name, n = spec.split("=")
        pool = [r for r in rows if r["stratum"] == name]
        sample += pool if int(n) == 0 or int(n) >= len(pool) else rng.sample(pool, int(n))
    with ThreadPoolExecutor(args.workers) as ex:
        results = list(ex.map(partial(check, config=config), sample))
    fields = list(dict.fromkeys(k for r in results for k in r))
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)
    print(json.dumps({"sampled": len(results), "flagged": sum(1 for r in results if r["flags"]),
                      "out": args.out}))


if __name__ == "__main__":
    main()
