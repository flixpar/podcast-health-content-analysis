"""Apple US top 24, month by month, from January 2016 (``apple-top24-monthly``).

The method is in ``apple_chart_monthly.py``. This study reads the chart
copies available when it was defined: the Marketing Tools feed, Apple's own
page, Podbay and Chartable. It does not use My Podcast Data, so from 2024-08
until live capture began it rests on Apple's 24-deep page alone;
``apple-top24-monthly-mpd`` is the same study with My Podcast Data added.
"""

from __future__ import annotations

from podcast_pipeline.studies.apple_chart_monthly import (
    APPLE_PAGE, CHARTABLE, MARKETING_TOOLS, PODBAY, AppleChartMonthly)


class AppleTop24Monthly(AppleChartMonthly):
    name = "apple-top24-monthly"
    description = ("Apple US overall chart, top 24 per calendar month since 2016-01 "
                   "(time-weighted points); each show's episodes from its charting months.")
    version = 3   # 2: midday-centred cells, nearest-in-time title ids; 3: no trailers, provisional months
    depth = 24
    sources = (MARKETING_TOOLS, APPLE_PAGE, PODBAY, CHARTABLE)
