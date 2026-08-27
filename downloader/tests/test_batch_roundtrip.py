import json
import sys
import types
from pathlib import Path

import pytest

from podcast_pipeline import db
from podcast_pipeline.audio import MIN_AUDIO_BYTES
from podcast_pipeline.batches import BatchFormatError, sha256_file
from podcast_pipeline.models import FeedEpisode, PodcastRecord, Segment
from podcast_pipeline.pipeline import (export_audio_batch, export_transcript_batch,
                                       import_transcript_batch, ingest_audio_batch,
                                       transcribe_audio_batch)
from podcast_pipeline.transcripts.store import TranscriptStore


def _source_batch(config, conn, tmp_path, count=2):
    config.download.min_free_gb = 0
    podcast_id = db.upsert_podcast(
        conn, PodcastRecord("apple_remote", "Remote Show", apple_podcasts_id="remote"),
    )
    episode_ids = []
    for index in range(1, count + 1):
        episode = FeedEpisode(
            f"remote-guid-{index}", f"Remote Episode {index}",
            f"https://x/{index}.mp3", duration_seconds=60 + index,
        )
        assert db.insert_episode(conn, podcast_id, episode)
        episode_id = conn.execute(
            "SELECT id FROM episodes WHERE episode_guid = ?", (episode.guid,),
        ).fetchone()[0]
        audio = config.audio_dir / "remote-show" / f"episode-{index}.ogg"
        audio.parent.mkdir(parents=True, exist_ok=True)
        audio.write_bytes(bytes([index]) * (MIN_AUDIO_BYTES + index * 100))
        db.record_download(conn, episode_id, audio, 1.0, 1.0, True)
        episode_ids.append(episode_id)
    conn.commit()
    transfer = tmp_path / "outbound"
    result = export_audio_batch.run(config, conn, transfer, target_gb=0.01)
    return episode_ids, result


def _install_fake_transcriber(monkeypatch):
    class Result:
        segments = [Segment("Remote words here.", 0.0, 2.5)]
        duration_seconds = 2.5
        chunk_count = 1
        rtf = 0.01

    class FakeTranscriber:
        def __init__(self, cfg, gpu_id):
            self.gpu_id = gpu_id

        def transcribe_file(self, path):
            assert path.is_file()
            return Result()

    fake_module = types.ModuleType("podcast_pipeline.asr.parakeet")
    fake_module.ParakeetTranscriber = FakeTranscriber
    fake_module.TranscriptionError = RuntimeError
    monkeypatch.setitem(sys.modules, "podcast_pipeline.asr.parakeet", fake_module)


def test_complete_remote_roundtrip_is_verified_resumable_and_idempotent(
        config, conn, tmp_path, monkeypatch):
    episode_ids, outbound = _source_batch(config, conn, tmp_path)
    workspace = tmp_path / "remote-workspace"
    ingested = ingest_audio_batch.run(
        Path(outbound["archive"]), workspace, checksum_path=Path(outbound["checksum"]),
    )
    batch_dir = Path(ingested["batch_dir"])
    assert ingested["episodes"] == 2
    assert json.loads((batch_dir / "ingest_receipt.json").read_text())["archive_sha256"] == (
        outbound["archive_sha256"]
    )
    repeated_ingest = ingest_audio_batch.run(
        Path(outbound["archive"]), workspace, checksum_path=Path(outbound["checksum"]),
    )
    assert repeated_ingest["already_prepared"] and repeated_ingest["batch_dir"] == str(batch_dir)

    _install_fake_transcriber(monkeypatch)
    config.transcription.gpu_ids = [0, 1]
    transcribed = transcribe_audio_batch.run(config, batch_dir)
    assert transcribed["transcribed"] == 2 and transcribed["failed"] == 0
    resumed = transcribe_audio_batch.run(config, batch_dir)
    assert resumed["queued"] == 0 and resumed["already_transcribed"] == 2

    returned_dir = tmp_path / "returned"
    preview = export_transcript_batch.run(batch_dir, returned_dir, dry_run=True)
    assert preview["complete"] and preview["transcripts"] == 2
    returned = export_transcript_batch.run(batch_dir, returned_dir)
    assert sha256_file(Path(returned["archive"])) == returned["archive_sha256"]

    dry_import = import_transcript_batch.run(
        config, conn, Path(returned["archive"]), checksum_path=Path(returned["checksum"]),
        dry_run=True,
    )
    assert dry_import["new"] == 2 and dry_import["already_imported"] == 0
    imported = import_transcript_batch.run(
        config, conn, Path(returned["archive"]), checksum_path=Path(returned["checksum"]),
    )
    assert imported["imported"] == 2

    for episode_id in episode_ids:
        row = conn.execute("""
            SELECT e.status, e.transcript_file_path, t.metadata
            FROM episodes e JOIN transcripts t ON t.episode_id = e.id WHERE e.id = ?
        """, (episode_id,)).fetchone()
        assert row["status"] == "transcribed"
        metadata = json.loads(row["metadata"])
        assert metadata["source_audio_batch_id"] == outbound["batch_id"]
        loaded = TranscriptStore(config.transcript_dir).load(Path(row["transcript_file_path"]))
        assert loaded.text == "Remote words here."

    repeated = import_transcript_batch.run(
        config, conn, Path(returned["archive"]), checksum_path=Path(returned["checksum"]),
    )
    assert repeated["imported"] == 0 and repeated["already_imported"] == 2


def test_batch_transcription_can_prefetch_decoded_audio(
        config, conn, tmp_path, monkeypatch):
    _, outbound = _source_batch(config, conn, tmp_path, count=3)
    ingested = ingest_audio_batch.run(
        Path(outbound["archive"]), tmp_path / "workspace",
        checksum_path=Path(outbound["checksum"]),
    )
    batch_dir = Path(ingested["batch_dir"])
    decoded_paths = []

    def fake_decode(path, sample_rate):
        decoded_paths.append(path)
        assert sample_rate == 16_000
        return [0.0] * sample_rate

    monkeypatch.setattr("podcast_pipeline.audio.ffmpeg.decode_pcm", fake_decode)

    class Result:
        segments = [Segment("Prefetched words.", 0.0, 1.0)]
        duration_seconds = 1.0
        chunk_count = 1
        rtf = 0.01

    class FakeTranscriber:
        def __init__(self, cfg, gpu_id):
            pass

        def transcribe_audio(self, audio):
            assert len(audio) == 16_000
            return Result()

    fake_module = types.ModuleType("podcast_pipeline.asr.parakeet")
    fake_module.ParakeetTranscriber = FakeTranscriber
    fake_module.TranscriptionError = RuntimeError
    monkeypatch.setitem(sys.modules, "podcast_pipeline.asr.parakeet", fake_module)
    config.transcription.gpu_ids = [0]
    config.transcription.decode_workers = 2
    config.transcription.decode_prefetch = 1

    result = transcribe_audio_batch.run(config, batch_dir)

    assert result["transcribed"] == 3
    assert len(decoded_paths) == 3


def test_ingest_rejects_bad_outer_checksum(config, conn, tmp_path):
    _, outbound = _source_batch(config, conn, tmp_path, count=1)
    bad_checksum = tmp_path / "bad.sha256"
    bad_checksum.write_text(f"{'0' * 64}  {Path(outbound['archive']).name}\n")
    with pytest.raises(BatchFormatError, match="Archive SHA-256 mismatch"):
        ingest_audio_batch.run(
            Path(outbound["archive"]), tmp_path / "workspace", checksum_path=bad_checksum,
        )
    assert not list((tmp_path / "workspace").glob(".batch-ingest-*.partial"))


def test_incomplete_batch_requires_explicit_partial_export(config, conn, tmp_path, monkeypatch):
    _, outbound = _source_batch(config, conn, tmp_path, count=2)
    ingested = ingest_audio_batch.run(
        Path(outbound["archive"]), tmp_path / "workspace",
        checksum_path=Path(outbound["checksum"]),
    )
    batch_dir = Path(ingested["batch_dir"])

    class Result:
        segments = [Segment("Worked.", 0.0, 1.0)]
        duration_seconds = 1.0
        chunk_count = 1
        rtf = 0.01

    class SometimesFails:
        def __init__(self, cfg, gpu_id):
            pass

        def transcribe_file(self, path):
            if path.name.endswith("2.ogg"):
                raise RuntimeError("bad audio")
            return Result()

    fake_module = types.ModuleType("podcast_pipeline.asr.parakeet")
    fake_module.ParakeetTranscriber = SometimesFails
    fake_module.TranscriptionError = RuntimeError
    monkeypatch.setitem(sys.modules, "podcast_pipeline.asr.parakeet", fake_module)
    config.transcription.gpu_ids = [0]

    result = transcribe_audio_batch.run(config, batch_dir)
    assert result["transcribed"] == 1 and result["failed"] == 1
    resumed = transcribe_audio_batch.run(config, batch_dir)
    assert resumed["queued"] == 0 and resumed["skipped_failed"] == 1
    with pytest.raises(export_transcript_batch.TranscriptBatchExportError, match="not complete"):
        export_transcript_batch.run(batch_dir, tmp_path / "return")
    partial = export_transcript_batch.run(
        batch_dir, tmp_path / "return", allow_partial=True,
    )
    assert not partial["complete"] and partial["transcripts"] == 1 and partial["missing"] == 1
