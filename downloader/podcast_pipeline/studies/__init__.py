"""Studies: named selections over the shared podcast catalog.

See ``base.py`` for what a study is and how to add one, and
``docs/studies.md`` (repository root) for the workflow.
"""

from __future__ import annotations

from podcast_pipeline.studies.apple_chart_monthly import (
    AppleTop24MonthlyMPD, AppleTop50Monthly, AppleTop100Monthly)
from podcast_pipeline.studies.apple_top24_monthly import AppleTop24Monthly
from podcast_pipeline.studies.base import Study
from podcast_pipeline.studies.corpus_2025 import Corpus2025

REGISTRY: dict[str, type[Study]] = {cls.name: cls for cls in (
    Corpus2025, AppleTop24Monthly, AppleTop24MonthlyMPD, AppleTop50Monthly, AppleTop100Monthly)}


def get(name: str) -> Study:
    try:
        return REGISTRY[name]()
    except KeyError:
        raise ValueError(f"Unknown study {name!r}; defined studies: {sorted(REGISTRY)}") from None
