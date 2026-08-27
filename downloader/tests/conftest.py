import shutil
import subprocess
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


@pytest.fixture
def one_frame_cover_art_ogg(tmp_path):
    """An Ogg with one Theora frame followed by 40 seconds of Opus audio."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not installed")
    cover = tmp_path / "cover.png"
    target = tmp_path / "one-frame-cover.ogg"
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=black:s=64x64",
            "-frames:v", "1", "-y", str(cover),
        ],
        check=True,
    )
    try:
        subprocess.run(
            [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                "-i", str(cover),
                "-f", "lavfi", "-i", "anoisesrc=d=40:c=pink:r=16000:s=123",
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libtheora", "-c:a", "libopus", "-b:a", "32k",
                "-y", str(target),
            ],
            check=True,
        )
    except subprocess.CalledProcessError:
        pytest.skip("ffmpeg lacks the libtheora or libopus encoder")
    return target
