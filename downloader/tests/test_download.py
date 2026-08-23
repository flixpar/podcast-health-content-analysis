from unittest.mock import Mock, patch

import pytest
import requests

from podcast_pipeline.audio import MIN_AUDIO_BYTES
from podcast_pipeline.audio.disk import DiskSpaceError
from podcast_pipeline.audio.download import AudioDownloader, DownloadError
from podcast_pipeline.audio.ffmpeg import EncodeError
from podcast_pipeline.config import CompressionConfig

BODY = b"x" * (MIN_AUDIO_BYTES + 1000)


def fake_response(body: bytes, status=200, headers=None):
    response = Mock()
    response.status_code = status
    response.headers = headers or {"content-length": str(len(body))}
    response.raise_for_status = Mock()
    response.iter_content = lambda chunk_size: (body[i:i + chunk_size] for i in range(0, len(body), chunk_size))
    return response


def downloader(tmp_path, session=None, **kwargs):
    return AudioDownloader(tmp_path, CompressionConfig(enabled=False), min_free_gb=0,
                           session=session or Mock(), **kwargs)


def test_fetch_writes_file_via_part(tmp_path):
    session = Mock()
    session.get.return_value = fake_response(BODY)
    dl = downloader(tmp_path, session)
    target = tmp_path / "ep.mp3"
    dl._fetch("https://x/ep.mp3", target)
    assert target.read_bytes() == BODY
    assert not target.with_suffix(".mp3.part").exists()


def test_fetch_resumes_partial_file(tmp_path):
    target = tmp_path / "ep.mp3"
    partial = tmp_path / "ep.mp3.part"
    partial.write_bytes(BODY[:500])
    session = Mock()
    session.get.return_value = fake_response(
        BODY[500:], status=206,
        headers={"content-length": str(len(BODY) - 500), "content-range": f"bytes 500-{len(BODY) - 1}/{len(BODY)}"},
    )
    downloader(tmp_path, session)._fetch("https://x/ep.mp3", target)
    assert session.get.call_args.kwargs["headers"] == {"Range": "bytes=500-"}
    assert target.read_bytes() == BODY


def test_fetch_restarts_when_server_ignores_range(tmp_path):
    target = tmp_path / "ep.mp3"
    (tmp_path / "ep.mp3.part").write_bytes(b"old" * 100)
    session = Mock()
    session.get.return_value = fake_response(BODY, status=200)
    downloader(tmp_path, session)._fetch("https://x/ep.mp3", target)
    assert target.read_bytes() == BODY


def test_incomplete_download_keeps_partial_for_resume(tmp_path):
    session = Mock()
    session.get.return_value = fake_response(BODY, headers={"content-length": str(len(BODY) * 2)})
    with pytest.raises(DownloadError, match="incomplete"):
        downloader(tmp_path, session)._fetch("https://x/ep.mp3", tmp_path / "ep.mp3")
    assert (tmp_path / "ep.mp3.part").exists()
    assert not (tmp_path / "ep.mp3").exists()


def test_tiny_response_is_discarded(tmp_path):
    session = Mock()
    session.get.return_value = fake_response(b"not audio")
    with pytest.raises(DownloadError, match="small"):
        downloader(tmp_path, session)._fetch("https://x/ep.mp3", tmp_path / "ep.mp3")
    assert not (tmp_path / "ep.mp3.part").exists()


def test_request_errors_become_download_errors(tmp_path):
    session = Mock()
    session.get.side_effect = requests.ConnectionError("refused")
    with pytest.raises(DownloadError, match="refused"):
        downloader(tmp_path, session)._fetch("https://x/ep.mp3", tmp_path / "ep.mp3")


def test_download_episode_reuses_existing_file(tmp_path):
    existing = tmp_path / "show" / "episode-1.mp3"
    existing.parent.mkdir()
    existing.write_bytes(BODY)
    session = Mock()
    result = downloader(tmp_path, session).download_episode("https://x/1.mp3", "Show", "Episode 1", "g")
    assert result.reused and result.path == existing and not result.is_compressed
    session.get.assert_not_called()


def test_download_halts_when_disk_is_full(tmp_path):
    dl = AudioDownloader(tmp_path, CompressionConfig(enabled=False), min_free_gb=10 ** 9, session=Mock())
    with pytest.raises(DiskSpaceError):
        dl.download_episode("https://x/1.mp3", "Show", "Episode 1", "g")


def test_download_episode_compresses_large_files(tmp_path):
    session = Mock()
    session.get.return_value = fake_response(BODY)
    dl = AudioDownloader(tmp_path, CompressionConfig(enabled=True, size_threshold_mb=0),
                         min_free_gb=0, session=session)

    def fake_encode(source, target, bitrate):
        target.write_bytes(b"o" * 1000)

    with patch("podcast_pipeline.audio.download.encode_opus", side_effect=fake_encode):
        result = dl.download_episode("https://x/1.mp3", "Show", "Episode 1", "g")
    assert result.is_compressed and result.path.suffix == ".ogg"
    assert not result.path.with_suffix(".mp3").exists()   # original removed after a verified encode
    assert result.compressed_size_mb < result.original_size_mb


def test_download_episode_keeps_mp3_when_encode_fails(tmp_path):
    session = Mock()
    session.get.return_value = fake_response(BODY)
    dl = AudioDownloader(tmp_path, CompressionConfig(enabled=True, size_threshold_mb=0),
                         min_free_gb=0, session=session)
    with patch("podcast_pipeline.audio.download.encode_opus", side_effect=EncodeError("short")):
        result = dl.download_episode("https://x/1.mp3", "Show", "Episode 1", "g")
    assert not result.is_compressed and result.path.suffix == ".mp3" and result.path.exists()
