import hashlib
import io
import json
import tarfile

import pytest

from podcast_pipeline.batches import BatchFormatError, stage_verified_archive


def test_safe_batch_extraction_rejects_traversal(tmp_path):
    archive = tmp_path / "bad.tar"
    payload = b"escape"
    with tarfile.open(archive, "w") as tar:
        member = tarfile.TarInfo("batch/../../outside.txt")
        member.size = len(payload)
        tar.addfile(member, io.BytesIO(payload))
    checksum = tmp_path / "bad.tar.sha256"
    checksum.write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  bad.tar\n")

    with pytest.raises(BatchFormatError, match="Unsafe"):
        stage_verified_archive(
            archive, tmp_path / "staging", allowed_exact={"manifest.jsonl"},
            allowed_prefix="audio/", checksum_path=checksum,
        )
    assert not (tmp_path / "outside.txt").exists()
    assert not list((tmp_path / "staging").glob(".batch-ingest-*.partial"))


def test_manifest_records_keep_unicode_line_separators_inside_strings():
    from podcast_pipeline.batches import _records

    title = "My Personal Chef  - Rémi\u0085Lauvand"
    payload = (json.dumps({"episode_id": 1, "title": title}, ensure_ascii=False) + "\r\n\n"
               + json.dumps({"episode_id": 2}, ensure_ascii=False) + "\n").encode()

    assert _records(payload, "manifest") == [{"episode_id": 1, "title": title}, {"episode_id": 2}]
