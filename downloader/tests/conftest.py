import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from podcast_pipeline import db  # noqa: E402
from podcast_pipeline.config import Config  # noqa: E402


@pytest.fixture
def config(tmp_path) -> Config:
    return Config(data_dir=str(tmp_path / "data"))


@pytest.fixture
def conn(config):
    connection = db.connect(config.db_path)
    yield connection
    connection.close()
