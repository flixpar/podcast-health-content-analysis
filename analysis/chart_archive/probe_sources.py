"""Count Wayback captures for candidate pre-2019 chart sources.

One sequential CDX request per candidate (the endpoint drops parallel ones),
writing a tally we can sort before spending any download time.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "data" / "chart-archive" / "index" / "probe.json"

CANDIDATES = {
    # Apple's own feeds, other spellings and hosts
    "apple_rss_nocountry": "itunes.apple.com/rss/toppodcasts",
    "apple_rss_ax": "ax.itunes.apple.com/WebObjects/MZStoreServices.woa/ws/RSS/toppodcasts",
    "apple_rss_mzstore": "itunes.apple.com/WebObjects/MZStoreServices.woa/ws/RSS/toppodcasts",
    "apple_com_charts": "apple.com/itunes/charts/podcasts",
    "apple_rss_audio": "itunes.apple.com/us/rss/topaudiopodcasts",
    "apple_rss_video": "itunes.apple.com/us/rss/topvideopodcasts",
    "apple_viewtop": "itunes.apple.com/WebObjects/MZStore.woa/wa/viewTop",
    # third-party chart mirrors that predate Chartable
    "podbay": "podbay.fm/browse/top",
    "podbay_charts": "podbay.fm/charts",
    "playerfm": "player.fm/featured",
    "itunescharts_net": "itunescharts.net",
    "podcastchart_com": "podcastchart.com",
    "toppodcast_com": "toppodcast.com",
    "stitcher_charts": "stitcher.com/charts",
    "blubrry_charts": "blubrry.com/podcast-charts",
    "podchaser_charts": "podchaser.com/charts",
    "podcharts_chart": "podcharts.co/chart",
    "podcastinsights_top": "podcastinsights.com/top-podcasts",
    "castbox_top": "castbox.fm/store",
    "listennotes_top": "listennotes.com/top-podcasts",
    "podtail_top": "podtail.com/top",
    "podcastaddict_top": "podcastaddict.com/top",
    "podsearch_top": "podsearch.com",
    "chartoo": "chartoo.com/podcasts",
    "podcastranker": "podcastranker.com",
    "podtrac_rankings": "podtrac.com/podcast-industry-audience-rankings",
    "tritondigital_ranker": "tritondigital.com/podcast-ranker",
}


def cdx(prefix: str, attempts: int = 4) -> str:
    url = ("http://web.archive.org/cdx/search/cdx"
           f"?url={prefix}&matchType=prefix&fl=timestamp,original"
           "&filter=statuscode:200&collapse=digest&limit=200000")
    delay = 12.0
    for _ in range(attempts):
        proc = subprocess.run(["curl", "-s", "--max-time", "240", url],
                              capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
        time.sleep(delay)
        delay = min(delay * 1.7, 90)
    return ""


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    have = json.loads(OUT.read_text()) if OUT.exists() else {}
    for name, prefix in CANDIDATES.items():
        if name in have:
            continue
        body = cdx(prefix)
        rows = [ln.split() for ln in body.splitlines() if ln.strip()]
        years: dict[str, int] = {}
        for ts, _url in ((r[0], r[1]) for r in rows if len(r) >= 2):
            years[ts[:4]] = years.get(ts[:4], 0) + 1
        pre2019 = sum(v for k, v in years.items() if k < "2019")
        have[name] = {"prefix": prefix, "captures": len(rows),
                      "pre_2019": pre2019, "by_year": dict(sorted(years.items()))}
        OUT.write_text(json.dumps(have, indent=2))
        print(f"{name:24s} {len(rows):7d} captures  ({pre2019} pre-2019)", flush=True)
        time.sleep(4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
