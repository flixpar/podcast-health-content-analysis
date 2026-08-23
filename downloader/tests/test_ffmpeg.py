import shutil
import subprocess

import pytest

from podcast_pipeline.audio.ffmpeg import EncodeError, check_conversion, decode_pcm, encode_opus, probe_duration

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
