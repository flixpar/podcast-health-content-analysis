import hashlib
import json
import tarfile
from pathlib import Path

from podcast_pipeline import db
from podcast_pipeline.audio import MIN_AUDIO_BYTES
from podcast_pipeline.models import FeedEpisode, PodcastRecord
from podcast_pipeline.pipeline import export_audio_batch


def _seed_episode(conn, podcast_id: int, guid: str, title: str) -> int:
    assert db.insert_episode(conn, podcast_id, FeedEpisode(guid, title, f"https://x/{guid}.mp3"))
    return conn.execute("SELECT id FROM episodes WHERE episode_guid = ?", (guid,)).fetchone()[0]


def _downloaded(conn, episode_id: int, path: Path, *, status: str = "downloaded") -> None:
    db.record_download(conn, episode_id, path, 1.0, 1.0, False)
    if status != "downloaded":
        conn.execute("UPDATE episodes SET status = ? WHERE id = ?", (status, episode_id))


def test_export_creates_self_describing_tar_and_skips_it_next_time(config, conn, tmp_path):
    config.download.min_free_gb = 0
    podcast_id = db.upsert_podcast(conn, PodcastRecord("apple_1", "A Show"))
    first = _seed_episode(conn, podcast_id, "g1", "First")
    retry = _seed_episode(conn, podcast_id, "g2", "Failed transcription")
    transcribed = _seed_episode(conn, podcast_id, "g3", "Already transcribed")
    missing = _seed_episode(conn, podcast_id, "g4", "Missing")
    tiny = _seed_episode(conn, podcast_id, "g5", "Tiny")
    pending = _seed_episode(conn, podcast_id, "g6", "Still downloading")

    audio_dir = config.audio_dir / "a-show"
    audio_dir.mkdir(parents=True)
    first_path = audio_dir / "first.ogg"
    retry_path = audio_dir / "retry.mp3"
    transcribed_path = audio_dir / "done.ogg"
    tiny_path = audio_dir / "tiny.mp3"
    first_bytes = b"a" * (MIN_AUDIO_BYTES + 17)
    retry_bytes = b"b" * (MIN_AUDIO_BYTES + 31)
    first_path.write_bytes(first_bytes)
    retry_path.write_bytes(retry_bytes)
    transcribed_path.write_bytes(b"c" * (MIN_AUDIO_BYTES + 1))
    tiny_path.write_bytes(b"small")
    (audio_dir / "still.mp3.part").write_bytes(b"partial")

    _downloaded(conn, first, first_path)
    _downloaded(conn, retry, retry_path, status="error")
    _downloaded(conn, transcribed, transcribed_path)
    _downloaded(conn, missing, audio_dir / "absent.mp3")
    _downloaded(conn, tiny, tiny_path)
    # A path on a pending row does not make an in-progress download eligible.
    conn.execute("UPDATE episodes SET audio_file_path = ? WHERE id = ?",
                 (str(audio_dir / "still.mp3.part"), pending))
    conn.execute("INSERT INTO transcripts (episode_id, file_path) VALUES (?, ?)",
                 (transcribed, str(config.transcript_dir / f"episode_{transcribed}.jsonl.zst")))
    conn.commit()

    output = tmp_path / "transfer"
    result = export_audio_batch.run(config, conn, output, target_gb=0.001)

    assert result["selected"] == 2
    assert result["rejected"] == {
        "already_exported": 0, "missing": 1, "not_regular": 0, "too_small": 1,
    }
    archive = Path(result["archive"])
    assert archive.exists() and not list(output.glob("*.partial"))
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == result["archive_sha256"]
    assert Path(result["checksum"]).read_text() == f"{result['archive_sha256']}  {archive.name}\n"

    with tarfile.open(archive) as tar:
        names = tar.getnames()
        root = result["batch_id"]
        assert f"{root}/audio/episode_{first}.ogg" in names
        assert f"{root}/audio/episode_{retry}.mp3" in names
        manifest_file = tar.extractfile(f"{root}/manifest.jsonl")
        assert manifest_file is not None
        records = [json.loads(line) for line in manifest_file]
        assert records[0]["episode_count"] == 2
        episodes = {record["episode_id"]: record for record in records[1:]}
        assert episodes[first]["sha256"] == hashlib.sha256(first_bytes).hexdigest()
        assert episodes[retry]["episode_status_at_export"] == "error"

    registry = Path(result["registry_manifest"])
    assert registry.read_bytes() == b"".join(
        (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        for record in records
    )
    again = export_audio_batch.run(config, conn, output, target_gb=0.001)
    assert again["selected"] == 0 and again["archive"] is None
    assert again["rejected"]["already_exported"] == 2


def test_dry_run_does_not_write_and_target_is_a_payload_cap(config, conn, tmp_path):
    podcast_id = db.upsert_podcast(conn, PodcastRecord("apple_1", "A Show"))
    sizes = [180_000, 150_000, 110_000]
    for index, size in enumerate(sizes, 1):
        episode_id = _seed_episode(conn, podcast_id, f"g{index}", f"Episode {index}")
        path = config.audio_dir / f"episode-{index}.mp3"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes([index]) * size)
        _downloaded(conn, episode_id, path)
    conn.commit()

    # Greedy selection skips the 150 kB file after taking 180 kB, then takes
    # the later 110 kB file to get closer to the 300 kB cap.
    output = tmp_path / "not-created"
    result = export_audio_batch.run(config, conn, output, target_gb=0.0003, dry_run=True)
    assert result["selected"] == 2
    assert result["selected_audio_bytes"] == 290_000
    assert result["not_selected_for_size"] == 1
    assert not output.exists()
    assert not config.batch_export_dir.exists()
