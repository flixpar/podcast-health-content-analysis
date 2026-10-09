"""Chart history: the reconstructed 2012-2026 archive and live daily captures.

``keys`` names charts and titles, ``archive_import`` loads the parsed archive
(``import-chart-archive``), ``capture`` records today's live charts
(``capture-charts``), and ``mypodcastdata`` backfills daily Apple charts from
2024-09 (``import-mypodcastdata``). All write ``chart_snapshots`` /
``chart_entries``.
"""
