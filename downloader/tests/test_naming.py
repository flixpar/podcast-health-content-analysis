from podcast_pipeline.audio import MIN_AUDIO_BYTES
from podcast_pipeline.audio.naming import episode_stem, find_existing_audio, normalize_id


def test_normalize_id():
    assert normalize_id("Héllo, World!") == "hello-world"
    assert normalize_id("  ") == "unknown"
    assert normalize_id(None) == "unknown"
    assert len(normalize_id("a" * 300)) == 100
    assert normalize_id("x-" * 60, max_length=5) == "x-x-x"


def test_episode_stem_hashes_guid():
    assert episode_stem("Episode 1", None) == "episode-1"
    hashed = episode_stem("Episode 1", "guid-123")
    assert hashed.startswith("episode-1_") and len(hashed) == len("episode-1_") + 8
    assert hashed != episode_stem("Episode 1", "guid-456")


def test_find_existing_audio_checks_both_schemes_and_formats(tmp_path):
    podcast_dir = tmp_path / "my-show"
    podcast_dir.mkdir()
    real = b"\0" * (MIN_AUDIO_BYTES + 1)

    assert find_existing_audio(tmp_path, "My Show", "Episode 1", "g") is None

    legacy_mp3 = podcast_dir / "episode-1.mp3"
    legacy_mp3.write_bytes(real)
    assert find_existing_audio(tmp_path, "My Show", "Episode 1", "g") == legacy_mp3

    hashed_ogg = podcast_dir / f"{episode_stem('Episode 1', 'g')}.ogg"
    hashed_ogg.write_bytes(real)
    assert find_existing_audio(tmp_path, "My Show", "Episode 1", "g") == hashed_ogg

    # A stub left by a failed download does not count.
    hashed_ogg.write_bytes(b"\0" * 10)
    assert find_existing_audio(tmp_path, "My Show", "Episode 1", "g") == legacy_mp3
