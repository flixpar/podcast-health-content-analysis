import json

import pytest

from podcast_pipeline.config import PROJECT_ROOT, Config, ConfigError


def test_defaults_and_derived_paths():
    config = Config()
    assert config.download.max_workers == 8
    assert config.transcription.gpu_ids == [0]
    assert not config.transcription.vad_enabled
    assert config.transcription.vad_threshold == 0.5
    assert config.batch_export.target_size_gb == 250.0
    assert config.db_path == PROJECT_ROOT / "data" / "podcast_metadata.db"
    assert config.audio_dir == PROJECT_ROOT / "data" / "audio"
    assert config.batch_export_dir == PROJECT_ROOT / "data" / "audio_batches"


def test_nested_override_keeps_other_defaults():
    config = Config.from_dict({"download": {"max_workers": 2}, "transcription": {"gpu_ids": [0, 1]}})
    assert config.download.max_workers == 2
    assert config.download.min_free_gb == 100.0
    assert config.transcription.gpu_ids == [0, 1]


def test_vad_settings_can_be_overridden():
    config = Config.from_dict({"transcription": {
        "vad_enabled": True,
        "vad_threshold": 0.65,
        "vad_min_silence_duration_ms": 500,
    }})
    assert config.transcription.vad_enabled
    assert config.transcription.vad_threshold == 0.65
    assert config.transcription.vad_min_silence_duration_ms == 500


def test_unknown_key_is_rejected():
    with pytest.raises(ConfigError, match="chunk_size"):
        Config.from_dict({"download": {"chunk_size": 8192}})
    with pytest.raises(ConfigError, match="processing"):
        Config.from_dict({"processing": {}})


def test_load_from_file_and_env(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"data_dir": str(tmp_path / "d"), "podchaser": {"client_id": "file"}}))
    monkeypatch.setenv("PODCHASER_CLIENT_ID", "env")
    config = Config.load(path)
    assert config.podchaser.client_id == "env"
    assert config.data_path == tmp_path / "d"


def test_missing_file():
    with pytest.raises(ConfigError, match="not found"):
        Config.load("/nonexistent/config.json")
