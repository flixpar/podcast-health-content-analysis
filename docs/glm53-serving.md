# Serving the v8 labeler

Use `analysis/serving/serve-glm53.sh` for the maintained GLM-5.3-Flash W4A16
configuration on four 80 GB H100s. It serves
`canada-quant/GLM-5.3-Flash-W4A16-MTP` as `glm53-w4` on port 8222.
The labeling workflow and v8 taxonomy are described in `docs/labeling.md`.

## Start and label

Activate a vLLM environment that supports this checkpoint, sparse MLA attention
and shared-prefix KDA checkpoints, or set `VLLM` to its executable. The
recorded runs used a vLLM nightly from September 2026 with CUDA 12.9;
recheck checkpoint support and the optional patch when changing vLLM versions.
The launchers use your normal Hugging Face and vLLM caches. `HF_HOME`,
`VLLM_CACHE_ROOT` and `XDG_CACHE_HOME` can select other directories.

```bash
analysis/serving/serve-glm53.sh
# Optional: explicit installation and port
VLLM=/path/to/vllm-environment/bin/vllm PORT=8222 analysis/serving/serve-glm53.sh

# In another terminal, after local transcripts have been collected:
.venv/bin/python analysis/topic_labeling.py prepare \
    --config analysis/topic-labeling-glm53.toml --limit 3
.venv/bin/python analysis/topic_labeling.py label \
    --config analysis/topic-labeling-glm53.toml
.venv/bin/python analysis/topic_labeling.py merge \
    --config analysis/topic-labeling-glm53.toml

# Benchmark data must already be populated under local/benchmark/v3.
BENCHMARK_DIR=benchmark/v3 .venv/bin/python -m analysis.benchmark run \
    --name glm53-high --pipeline-config benchmark/pipeline-glm53.toml \
    --repeats 1 --split all
```

`BENCHMARK_DIR` selects the tracked benchmark specification; its configured
local data directory contains items, gold and candidate runs.
`BENCHMARK_OUTPUT_DIR` can override that data directory.
The shipped GLM config targets a local server.

## Defaults and capacity

| Setting | GLM default | Purpose |
| --- | --- | --- |
| Context | 196608 tokens | Fits the shared ~87k-token v8 instructions and output budget |
| Running sequences | 160 | Keeps the shared-prefix checkpoint in the KV pool |
| GPU memory utilization | 0.95 | Measured on four 80 GB H100s |
| KDA state | float32 | Works without the optional vLLM patch |
| Prefix caching | Shared-prefix KDA checkpoint enabled | Reuses the long codebook across requests |
| Speculative decoding | Off | MTP state reduced usable capacity in these measurements |
| Server CPU threads | 1 per worker | Avoids CPU oversubscription |
| Requests | Chat Completions, high effort, 24k thinking budget | Matches measured v8 workload |
| Output cap | 40000 tokens | Allows answers while bounding occasional generation loops |
| Client concurrency | 448 | Keeps the 160–224 server slots fed; excess requests queue |

Environment overrides include `MAX_NUM_SEQS`, `MAX_MODEL_LEN`,
`GPU_MEMORY_UTILIZATION`, `PORT`, `API_SERVER_COUNT`, `VLLM_OMP_NUM_THREADS`,
`VLLM_ENGINE_READY_TIMEOUT_S` and `VLLM_CHAT_TEMPLATE_RENDER_TIMEOUT`.
Extra command-line flags pass through to vLLM. `SPEC` accepts an explicit
speculative-decoding JSON config for controlled comparisons.

For the recorded 1,500-window corpus workload, default fp32 state at cap 160
achieved ~6,660 windows/hour steady and ~5,250 including the tail. Patched bf16
state at cap 224 achieved ~8,220 steady and ~6,340 including the tail. These
are historical measurements on that workload. Keep
`vllm:kv_cache_usage_perc` below about 0.8 and preemptions at zero; lower the
cap for denser windows. A full pool can evict the shared checkpoint and cause
repeated codebook prefill. The bf16 cap-256 run reached 0.94 KV use and
75 preemptions, with lower throughput.

In the historical comparison, v8 model outputs on 160 archived headline items
were scored against v7 gold through the v8-to-v7 label map. High/24k measured
topic F1 0.709 and claim F1 0.783 at 6.6k output tokens/window; these figures
do not validate the revised v8 rules. Fresh v3 reference annotation remains
pending, as described in `docs/benchmark.md`. Max effort used 15.2k tokens/window;
an 8k thinking budget saved only ~8% on real traffic and lost population F1.
High/24k remains the default. The historical codebook comparison favored using
the annotator codebook directly; a co-label prompt improved agreement with
one annotator family while reducing mean agreement, so it was not adopted.

## Optional bf16 state and CUDA paths

The preserved patch at
`analysis/serving/patches/vllm-glm5next-kda-state-dtype.patch` passes
`mamba_ssm_cache_dtype` through two GLM KDA call sites. Apply it to the matching
vLLM installation only if that version still ignores the setting. For example,
activate the vLLM environment and locate its installed package before applying:

```bash
VLLM_SITE=$(python -c 'import pathlib, vllm; print(pathlib.Path(vllm.__file__).resolve().parent.parent)')
patch -d "$VLLM_SITE" -p1 < analysis/serving/patches/vllm-glm5next-kda-state-dtype.patch
KDA_STATE_DTYPE=bfloat16 analysis/serving/serve-glm53.sh
```

The launcher checks the installed KDA source and refuses bf16 mode when the
setting is absent. It finds Python beside the resolved vLLM executable;
`VLLM_PYTHON` can explicitly select that installation's interpreter. Patched
bf16 mode defaults to cap 224. Recorded paired differences on the same older,
mapped gold were within run-to-run variation; this remains an opt-in setting.

No private cluster paths or environment modules are loaded by the scripts.
If your driver needs compatibility libraries, explicitly set `CUDA_COMPAT` to
the installed compatibility directory. Set `CUDA_HOME` to a matching toolkit
when JIT compilation needs one. Existing `LD_LIBRARY_PATH` entries are retained.

## Other launchers and throughput probe

`serve-deepseek-v4.sh` retains the DeepSeek checkpoint and reasoning-parser
plugin, with a default sequence cap of 512 and 196608-token context. The context
fits the longer v8 prompt plus the configured output budget; `MAX_MODEL_LEN`
remains overridable. The alternative-model
`serve-model.sh` supports Qwen, GPT-OSS and Gemma configurations with either
tensor or data parallelism. Select the model name as its first argument.
For offline GPT-OSS tokenizer vocabularies, set `TIKTOKEN_ENCODINGS_BASE` to
your downloaded vocabulary directory; otherwise normal tokenizer cache and
download behavior applies. The fast parser plugin depends on vLLM's parser
internals and should be rechecked after upgrades.

The reusable throughput probe stays with the serving tools:

```bash
BENCHMARK_DIR=benchmark/v3 .venv/bin/python analysis/serving/loadtest.py \
    --base http://127.0.0.1:8222 --concurrency 160 --seconds 240 --warmup 60 \
    --effort high --max-tokens 40000 --thinking-token-budget 24000
```

It reads the selected benchmark's local items/taxonomy, or explicit `--items`
and `--taxonomy` files, and records results under ignored
`local/serving/loadtest.jsonl` (`--out` overrides this). It sends labeling
traffic to the selected server. Detailed superseded experiment reports,
one-off scripts, rubric variants and private-node configs are preserved
under ignored `local/`.
