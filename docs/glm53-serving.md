# Labeling with GLM-5.3-Flash: serving and settings

GLM-5.3-Flash (`canada-quant/GLM-5.3-Flash-W4A16-MTP`: INT4 routed experts, BF16
attention, MTP head) labels the v8 scheme at least as well as DeepSeek-V4-Flash
with less than half the output tokens, and once served for this workload one
4x H100 node labels ~6,000 real windows an hour against ~4,250 for DeepSeek. One
v8 pass over 100k episodes (~1.54M windows) is ~255-290 node-hours.

```bash
analysis/serving/serve-glm53.sh                       # port 8222, served as glm53-w4
.venv/bin/python analysis/topic_labeling.py label --config analysis/topic-labeling-glm53.toml
# benchmark
BENCHMARK_DIR=benchmark/v3 .venv/bin/python -m analysis.benchmark run --name glm53-high \
    --pipeline-config benchmark/pipeline-glm53.toml --repeats 1 --split all
```

The experiments behind this are on branch `exp/v7-v8-labeling-methods`
(`docs/labeling-methods-v7-v8.md`, `docs/labeling-throughput-glm-tools.md`).
Quality figures below are the v8 benchmark's headline items (160) scored on the
v7 gold through the v8-to-v7 label map; one GLM run differs from another by
0.01-0.04 per axis.

## Quality and cost (v8 benchmark headline)

| configuration | topic F1 | claim F1 | output tokens / window |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash high, 24k budget | 0.678 | 0.755 | 13.1k |
| **GLM-5.3-Flash high, 24k budget (default)** | **0.709** | **0.783** | **6.6k** |
| GLM high, 8k budget | 0.689 | 0.767 | 5.4k |
| GLM max, 24k budget | 0.718 | 0.817 | 15.2k |
| GLM low | 0.647 | 0.692 | 2.4k |

The default is `high` with a 24k thinking budget. `max` buys evidence (+0.06)
and claim recall (+0.06) for 2.3x the tokens; an 8k budget saves ~8% on real
traffic and costs population F1 (-0.10); `low`, a 4k budget and thinking off
lose on every axis. `max_output_tokens` is 40k (the budget plus room for the
answer): ~0.1-0.3% of windows loop after thinking ends, and without a cap each
one runs to the limit while holding a server slot for most of an hour; a
truncated response is retried.

## Why the server is configured as it is

GLM-5.3-Flash is a hybrid of 34 linear-attention (KDA) layers and 11 sparse
MLA attention layers. Two consequences dominate throughput when every request
shares an 87k-token codebook:

1. **Prefix caching needs linear-attention state checkpoints.** vLLM runs it in
   "align" mode (1,152-token blocks): a request reuses the cached codebook only
   where a state checkpoint exists. `--enable-mamba-shared-prefix-checkpoint`
   registers one at the end of the shared prefix, so requests reuse 84-86k of
   the ~87.6k prompt tokens.
2. **Each running request holds a fixed block of linear-attention state**:
   ~8.6k token-equivalents of the KV pool without speculative decoding, ~14.7k
   with MTP-2 (whose head also shrinks the pool from 2.15M to 1.50M tokens).
   When the pool fills, vLLM evicts the shared-prefix checkpoint, later
   requests miss the cache entirely, re-prefill the codebook and hold their own
   copy of it, and the server preempts and recomputes. On dense windows it fell
   to 17 running requests and ~260 windows/h. **Cap concurrency below that
   point** with `--max-num-seqs`.

Throughput on real corpus windows (4x H100, v8 prompt, high/24k; 20-minute
fixed-horizon runs, which overstate absolute rates by ~25% but compare configs
under identical load):

| server configuration | windows/h | running | preemptions |
| --- | --- | --- | --- |
| MTP-2, prefix caching (first setup) | ~2,100 | 44 | 3/min |
| + shared-prefix checkpoint | 3,940 | 61 | 4.6/min |
| + cap at 48 sequences | 5,840 | 48 | 0 |
| **checkpoint, no speculation, cap at 128 (default)** | **7,480** | 128 | 0 |
| + CPU KV offloading (400 GiB) | ~2,200 | 15 | 0 |

A complete run of 1,500 random windows on the default configuration took 17
minutes: 6,040 windows/h in steady state, 5,300 including the tail, 2.2k output
tokens per window on average (median 384). KV use peaked near 66%, so
`MAX_NUM_SEQS` can likely go somewhat higher; raise it while
`vllm:kv_cache_usage_perc` stays under ~0.8 and preemptions stay at zero, and
lower it for traffic denser in health content than the corpus.

What did not help on this node:

- **MTP speculative decoding** (`SPEC='{"method":"mtp","num_speculative_tokens":2}'`):
  faster sequences, but half as many fit; loses once concurrency is capped.
- **CPU KV offloading** (`--kv-offloading-size`): removes preemption recompute,
  but requests restored from CPU hold private copies of the shared prefix.
- **fp8 KV cache** (not measured): the `FLASH_ATTN_MLA_SPARSE` backend used here
  is bf16-only, but this vLLM nightly's `FLASHINFER_MLA_SPARSE_SM90` backend
  supports fp8 KV with this model's NoPE attention on Hopper (per-tensor scale
  only, `--max-model-len` capped at 131072). The expected gain is small: ~80%
  of each request's KV footprint is the fp32 linear-attention state, which fp8
  KV does not touch, so it would allow ~15% more concurrent requests and
  barely change decode speed. A bigger lever is that the linear-attention
  state is fp32 and `--mamba-ssm-cache-dtype bfloat16` is ignored by this
  model's vLLM implementation; a two-line patch to pass it through could allow
  ~50% more concurrent requests, at some risk to numerics over long outputs.
  Neither has been tried.
- **DFlash2-G drafter**: does not load on upstream vLLM; the model card's
  numbers use a patched image, and it cuts the KV pool ~6x at TP4.
- **NVFP4 checkpoint**: FP4 is emulated on Hopper and slower than W4A16.

Other flags: `--api-server-count 4` and `VLLM_CHAT_TEMPLATE_RENDER_TIMEOUT=600`
keep the API process from timing out when hundreds of 87k-token prompts are
queued at once; `--attention-backend FLASH_ATTN_MLA_SPARSE` because the
default backend faults on long prompts (model card); `--language-model-only`
skips the vision tower.

## Installing on gpu313 (driver 570)

The model needs a vLLM nightly from 2026-09-08 or later, published only for
cu129:

```bash
uv venv /scratch/fparker9/vllm-nightly-venv --python 3.12
uv pip install --python /scratch/fparker9/vllm-nightly-venv vllm --pre \
    --extra-index-url https://wheels.vllm.ai/nightly/cu129 \
    --extra-index-url https://download.pytorch.org/whl/cu129 --index-strategy unsafe-best-match
uv pip uninstall --python /scratch/fparker9/vllm-nightly-venv torchcodec   # wants libnvrtc.so.13
```

Driver 570 cannot JIT the cu129 wheel's PTX, so the serve script puts NVIDIA's
CUDA 12.9 forward-compatibility `libcuda` (rpm `cuda-compat-12-9`, unpacked to
`CUDA_COMPAT`) on `LD_LIBRARY_PATH`. DeepGEMM (the sparse-attention indexer) and
FlashInfer compile kernels at startup with nvcc >= 12.9 and the cuRAND headers,
so `CUDA_HOME` points at a user-space CUDA 12.9 toolkit unpacked from NVIDIA's
rpms (nvcc, crt, nvvm, cudart, cccl, nvrtc, driver-devel, libcurand, nvtx,
profiler-api). Both are skipped when the directories do not exist, for nodes
with a newer driver. HF downloads go through the JHU proxy
(`HTTPS_PROXY=http://proxy.jh.edu:3129/`); the weights are 178 GB.
