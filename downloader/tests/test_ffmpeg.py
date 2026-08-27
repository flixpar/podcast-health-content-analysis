import os
import shutil
import subprocess

import pytest

from podcast_pipeline.audio.ffmpeg import (
    EncodeError,
    check_conversion,
    decode_pcm,
    encode_opus,
    probe_duration,
    probe_stream_types,
)

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


@pytest.fixture(scope="module")
def noise_mp3(tmp_path_factory):
    path = tmp_path_factory.mktemp("audio") / "noise.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anoisesrc=d=90:c=pink",
                    "-c:a", "libmp3lame", "-b:a", "128k", str(path)], check=True)
    return path


def test_probe_duration(noise_mp3, tmp_path):
    assert probe_duration(noise_mp3) == pytest.approx(90, abs=0.5)
    bogus = tmp_path / "bogus.mp3"
    bogus.write_bytes(b"nope")
    assert probe_duration(bogus) is None


def test_encode_opus_roundtrip(noise_mp3, tmp_path):
    target = tmp_path / "noise.ogg"
    encode_opus(noise_mp3, target)
    assert target.exists()
    assert check_conversion(noise_mp3, target) is None
    assert probe_duration(target) == pytest.approx(90, abs=0.5)


def test_encode_opus_strips_one_frame_cover_art(one_frame_cover_art_ogg, tmp_path):
    assert probe_stream_types(one_frame_cover_art_ogg) == ("video", "audio")
    target = tmp_path / "audio-only.ogg"

    encode_opus(one_frame_cover_art_ogg, target)

    assert probe_stream_types(target) == ("audio",)
    assert check_conversion(one_frame_cover_art_ogg, target) is None


def test_conversion_rejects_extra_streams(one_frame_cover_art_ogg):
    assert "exactly one audio stream" in check_conversion(
        one_frame_cover_art_ogg, one_frame_cover_art_ogg,
    )


def test_truncated_encode_is_rejected(noise_mp3, tmp_path):
    short = tmp_path / "short.ogg"
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(noise_mp3), "-t", "45",
                    "-c:a", "libopus", "-b:a", "64k", str(short)], check=True)
    assert "short" in check_conversion(noise_mp3, short)


def test_encode_failure_leaves_no_output(tmp_path):
    bogus = tmp_path / "bogus.mp3"
    bogus.write_bytes(b"nope")
    target = tmp_path / "bogus.ogg"
    with pytest.raises(EncodeError):
        encode_opus(bogus, target)
    assert not target.exists()


def test_decode_pcm(noise_mp3):
    samples = decode_pcm(noise_mp3, 16000)
    assert samples.dtype.name == "float32"
    assert len(samples) == pytest.approx(90 * 16000, rel=0.01)


def _stub_tool(directory, name, exit_code):
    """A fake ffmpeg/ffprobe that writes undecodable bytes to stderr."""
    directory.mkdir(exist_ok=True)
    tool = directory / name
    # 0xe2 starts a 3-byte sequence; '(' is not a valid continuation byte.
    tool.write_bytes(b"#!/bin/sh\nprintf 'title: \\342( oops' >&2\nexit %d\n" % exit_code)
    tool.chmod(0o755)
    return tool


def test_encode_reports_non_utf8_stderr(tmp_path, monkeypatch):
    """ffmpeg echoes ID3 tags verbatim, so its stderr is not always UTF-8.

    Decoding it strictly turned a plain encode failure into a UnicodeDecodeError
    that escaped the EncodeError handling and failed the episode outright.
    """
    fake_bin = tmp_path / "bin"
    _stub_tool(fake_bin, "ffmpeg", exit_code=1)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    source = tmp_path / "in.mp3"
    source.write_bytes(b"nope")
    target = tmp_path / "out.ogg"

    with pytest.raises(EncodeError, match=r"ffmpeg failed \(1\)"):
        encode_opus(source, target)
    assert not target.exists()


def test_probe_duration_survives_non_utf8_stderr(tmp_path, monkeypatch):
    fake_bin = tmp_path / "bin"
    _stub_tool(fake_bin, "ffprobe", exit_code=1)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    assert probe_duration(tmp_path / "in.mp3") is None
