"""Serving command contracts, using local stubs rather than models or GPUs."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from analysis.serving import loadtest


ROOT = Path(__file__).resolve().parents[2]
SERVING = ROOT / "analysis/serving"


@pytest.fixture
def stub_env(tmp_path):
    executable = tmp_path / "vllm"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "keys = ('PATH', 'HF_HOME', 'VLLM_CACHE_ROOT', 'TIKTOKEN_ENCODINGS_BASE', "
        "'LD_LIBRARY_PATH', 'OMP_NUM_THREADS', 'CUDA_HOME')\n"
        "print(json.dumps({'args': sys.argv[1:], 'env': {key: os.environ[key] for key in keys if key in os.environ}}))\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    env = {key: value for key, value in os.environ.items() if key not in {
        "VLLM", "VLLM_PYTHON", "MAX_NUM_SEQS", "MAX_MODEL_LEN", "PORT", "SPEC",
        "KDA_STATE_DTYPE", "CUDA_HOME", "CUDA_COMPAT", "LD_LIBRARY_PATH", "PARALLEL",
        "HF_HOME", "VLLM_CACHE_ROOT", "TIKTOKEN_ENCODINGS_BASE", "VLLM_OMP_NUM_THREADS",
    }}
    env["PATH"] = str(tmp_path) + os.pathsep + env["PATH"]
    env["XDG_CACHE_HOME"] = str(tmp_path / "cache")
    return env


def launch(script, env, *args, check=True):
    return subprocess.run(
        ["bash", str(SERVING / script), *args], env=env,
        capture_output=True, text=True, check=check,
    )


def flag(args, name):
    return args[args.index(name) + 1]


@pytest.mark.parametrize("script,model,cap", [
    ("serve-glm53.sh", "canada-quant/GLM-5.3-Flash-W4A16-MTP", "160"),
    ("serve-deepseek-v4.sh", "deepseek-ai/DeepSeek-V4-Flash-0731", "512"),
    ("serve-model.sh", "openai/gpt-oss-120b", "256"),
])
def test_launchers_find_vllm_on_path_and_keep_cache_overrides(stub_env, script, model, cap):
    model_args = ["gpt-oss-120b"] if script == "serve-model.sh" else []
    default = json.loads(launch(script, stub_env, *model_args).stdout)
    assert default["args"][:2] == ["serve", model]
    assert flag(default["args"], "--max-num-seqs") == cap
    assert flag(default["args"], "--max-model-len") == ("96K" if script == "serve-model.sh" else "196608")
    assert default["env"]["HF_HOME"] == str(Path(stub_env["XDG_CACHE_HOME"]) / "huggingface")
    assert default["env"]["VLLM_CACHE_ROOT"] == str(Path(stub_env["XDG_CACHE_HOME"]) / "vllm")
    assert "TIKTOKEN_ENCODINGS_BASE" not in default["env"]

    env = {**stub_env, "MAX_NUM_SEQS": "32", "MAX_MODEL_LEN": "128K", "PORT": "8999",
           "HF_HOME": "/chosen/hf", "VLLM_CACHE_ROOT": "/chosen/vllm",
           "TIKTOKEN_ENCODINGS_BASE": "/chosen/vocab"}
    overridden = json.loads(launch(script, env, *model_args, "--disable-log-requests").stdout)
    assert flag(overridden["args"], "--max-num-seqs") == "32"
    assert flag(overridden["args"], "--max-model-len") == "128K"
    assert flag(overridden["args"], "--port") == "8999"
    assert overridden["args"][-1] == "--disable-log-requests"
    for key in ("HF_HOME", "VLLM_CACHE_ROOT", "TIKTOKEN_ENCODINGS_BASE"):
        assert overridden["env"][key] == env[key]


@pytest.mark.parametrize("name,model,parser", [
    ("qwen3.5-35b-a3b", "Qwen/Qwen3.5-35B-A3B-FP8", "qwen3_fast"),
    ("qwen3.8-flash-next", "Qwen/Qwen3.8-Flash-Next-FP8", "qwen3_fast"),
    ("gpt-oss-120b", "openai/gpt-oss-120b", "openai_gptoss"),
    ("gemma-4-26b-a4b", "google/gemma-4-26B-A4B-it", "gemma4_fast"),
])
def test_generic_launcher_models_and_data_parallelism(stub_env, name, model, parser):
    output = json.loads(launch("serve-model.sh", {**stub_env, "PARALLEL": "dp"}, name).stdout)
    args = output["args"]
    assert args[:2] == ["serve", model]
    assert flag(args, "--reasoning-parser") == parser
    assert flag(args, "--data-parallel-size") == "4"
    assert flag(args, "--tensor-parallel-size") == "1"
    assert "--enable-expert-parallel" not in args
    if name != "gpt-oss-120b":
        assert Path(flag(args, "--reasoning-parser-plugin")) == SERVING / "fast_reasoning_end_plugin.py"


def test_glm_optional_cuda_paths_do_not_require_existing_library_path(stub_env, tmp_path):
    toolkit = tmp_path / "cuda"
    toolkit.mkdir()
    compat = tmp_path / "compat"
    compat.mkdir()
    env = {**stub_env, "CUDA_HOME": str(toolkit), "CUDA_COMPAT": str(compat)}
    output = json.loads(launch("serve-glm53.sh", env).stdout)
    assert output["env"]["LD_LIBRARY_PATH"] == f"{toolkit}/targets/x86_64-linux/lib:{compat}"
    assert output["env"]["PATH"].startswith(f"{toolkit}/bin:")
    assert output["env"]["OMP_NUM_THREADS"] == "1"


@pytest.mark.parametrize("patched", [False, True])
def test_glm_bf16_requires_patch_and_changes_capacity(stub_env, tmp_path, patched):
    kda = tmp_path / "kda.py"
    kda.write_text("mamba_ssm_cache_dtype\n" if patched else "unpatched\n", encoding="utf-8")
    interpreter = tmp_path / "python"
    interpreter.write_text(f"#!{sys.executable}\nprint({str(kda)!r})\n", encoding="utf-8")
    interpreter.chmod(0o755)
    env = {**stub_env, "KDA_STATE_DTYPE": "bfloat16"}
    result = launch("serve-glm53.sh", env, check=False)
    if patched:
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert flag(output["args"], "--max-num-seqs") == "224"
        assert flag(output["args"], "--mamba-ssm-cache-dtype") == "bfloat16"
    else:
        assert result.returncode == 2
        assert "needs the vLLM patch" in result.stderr
        assert not result.stdout


def test_glm_explicit_executable_interpreter_and_speculation(stub_env, tmp_path):
    kda = tmp_path / "kda.py"
    kda.write_text("mamba_ssm_cache_dtype\n", encoding="utf-8")
    interpreter = tmp_path / "custom-python"
    interpreter.write_text(f"#!{sys.executable}\nprint({str(kda)!r})\n", encoding="utf-8")
    interpreter.chmod(0o755)
    spec = '{"method":"mtp","num_speculative_tokens":2}'
    env = {**stub_env, "VLLM": str(tmp_path / "vllm"), "VLLM_PYTHON": str(interpreter),
           "KDA_STATE_DTYPE": "bfloat16", "MAX_NUM_SEQS": "48", "SPEC": spec}
    output = json.loads(launch("serve-glm53.sh", env).stdout)
    assert flag(output["args"], "--max-num-seqs") == "48"
    assert flag(output["args"], "--speculative-config") == spec


def test_loadtest_metrics_accept_labeled_and_unlabeled_series(monkeypatch):
    class Response:
        text = (
            'vllm:generation_tokens_total{engine="0"} 10\n'
            'vllm:generation_tokens_total{engine="1"} 20\n'
            'vllm:kv_cache_usage_perc{engine="0"} 0.7\n'
            'vllm:kv_cache_usage_perc{engine="1"} 0.6\n'
            'vllm:num_requests_running 3\n'
        )

        def raise_for_status(self):
            pass

    monkeypatch.setattr(loadtest.requests, "get", lambda *args, **kwargs: Response())
    assert loadtest.metrics() == {
        "generation_tokens_total": 30.0, "num_requests_running": 3.0,
        "kv_cache_usage_perc": 0.7,
    }


def test_relocated_loadtest_help_works_outside_repository(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SERVING / "loadtest.py"), "--help"], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    )
    for flag_name in ("--items", "--taxonomy", "--out", "--thinking-token-budget"):
        assert flag_name in result.stdout


def test_loadtest_writes_selected_output_with_offline_server_stubs(tmp_path, monkeypatch, capsys):
    clock = {"now": 0.0}
    loaded = []
    taxonomy = loadtest.tl.compile_taxonomy(ROOT / "taxonomy/health-v8.md")
    item = {"window_id": "w1", "episode_id": 1, "window_index": 0, "units": []}
    monkeypatch.setattr(loadtest, "load_benchmark_taxonomy", lambda path: loaded.append(path) or taxonomy)
    monkeypatch.setattr(loadtest, "load_items", lambda path: loaded.append(path) or [item])

    class Thread:
        def __init__(self, **kwargs):
            pass

        def start(self):
            pass

    class Models:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"id": "stub-model"}]}

    def metrics():
        return {"generation_tokens_total": clock["now"] * 100,
                "prompt_tokens_total": clock["now"] * 50,
                "iteration_tokens_total_count": clock["now"] * 10,
                "iteration_tokens_total_sum": clock["now"] * 100,
                "num_requests_running": 1, "num_requests_waiting": 0,
                "kv_cache_usage_perc": 0.5, "num_preemptions_total": 0}

    def stop(status):
        raise SystemExit(status)

    out = tmp_path / "results/probe.jsonl"
    monkeypatch.setattr(loadtest.threading, "Thread", Thread)
    monkeypatch.setattr(loadtest.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(loadtest.time, "sleep", lambda seconds: clock.update(now=clock["now"] + seconds))
    monkeypatch.setattr(loadtest.requests, "get", lambda *args, **kwargs: Models())
    monkeypatch.setattr(loadtest, "metrics", metrics)
    monkeypatch.setattr(loadtest.os, "_exit", stop)
    monkeypatch.setattr(sys, "argv", ["loadtest", "--seconds", "1", "--warmup", "0",
                                      "--items", "chosen-items.jsonl", "--taxonomy", "chosen-taxonomy.json",
                                      "--out", str(out), "--thinking-token-budget", "24000"])
    with pytest.raises(SystemExit) as stopped:
        loadtest.main()
    assert stopped.value.code == 0
    assert loaded == [Path("chosen-taxonomy.json"), Path("chosen-items.jsonl")]
    result = json.loads(out.read_text())
    assert result["model"] == "stub-model"
    assert result["seconds"] == 1
    assert result["gen_tok_s"] == 100
    assert result["max_tokens"] == 40000
    assert result["thinking_token_budget"] == 24000
    assert json.loads(capsys.readouterr().out) == result
