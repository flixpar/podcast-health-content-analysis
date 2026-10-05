# Throughput, GLM-5.3-Flash variants, tool-based labeling and what to drop (2026-10-05)

Follow-up to `docs/labeling-methods-v7-v8.md`. Four questions:

- (a) how fast each labeling method is on real traffic, and how to make it faster;
- (b) whether a GLM-5.3-Flash configuration (reasoning level, thinking budget,
  system prompt, thinking on/off, serving config) balances quality and throughput
  better than the single run so far;
- (c) whether a tool-based labeler (labels submitted through tools, reasoning
  interleaved with tool calls) helps;
- (d) which parts of the label set cost the most for what they give, and so
  are candidates to drop.

All runs are on one node (gpu313, 4x H100 80GB, 16 CPU cores, driver 570),
v8 labels (benchmark/v3, the ~87k-token prompt) unless noted.

## Summary

**(a) Throughput.** On real traffic, one node (4x H100) labels ~6,000 windows
an hour with GLM-5.3-Flash once it is served properly, against ~4,250 for
DeepSeek-V4-Flash: one v8 pass over 100k episodes (1.54M windows) is ~255-290
node-hours with GLM and ~360-400 with DeepSeek. Keyword methods and the
TF-IDF screen are effectively free; a Clef-flash screen costs ~33 node-hours
per 100k episodes and saves ~11% of the LLM's work. The biggest optimization
was serving, not prompting: GLM went from ~1,500-2,100 windows/h as first
served to ~6,000 (3-4x) with two changes, `--enable-mamba-shared-prefix-checkpoint`
and a concurrency cap below the point where the KV pool saturates (no
speculative decoding, `--max-num-seqs 128`). Without the cap the hybrid
model's cache spirals: the shared 87k-token prefix is evicted, requests hold
private copies, and the server preempts and recomputes. CPU KV offloading
made it worse (requests restored from CPU do not share the prefix).

**(b) GLM-5.3-Flash configurations.** No configuration beats high effort with a
24k budget on both quality and cost by more than run-to-run noise (which is
±0.01-0.04 per axis for one run). The useful dials:
- an 8k thinking budget: -8% tokens on real traffic, quality within noise
  except populations (-0.10);
- max effort: 2.3x the tokens for better evidence (+0.06) and claim recall
  (+0.06), topics unchanged;
- low effort, a 4k budget and thinking off are clearly worse (topic F1 0.65,
  0.65, 0.55);
- a system-prompt note asking for efficient thinking: no effect;
- DFlash2-G, NVFP4 and fp8 KV are not usable or not helpful on this H100 node;
  MTP-2 helps per-sequence speed but loses to no-speculation once concurrency
  is capped, because its per-request state is 70% larger.
Qwen3.8-Flash-Next (xhigh) matches GLM on topics and has the best one-pass
claim F1, but thinks 2.5x as long and runs ~4x slower; its union with GLM is
a quality option (best narrative F1 of any GLM configuration) at ~1.6x the
tokens of GLM + GLM refine.

**(c) Tool-based labeling** (incremental add-tools with validation feedback,
submit-and-revise, and a lookup tool replacing the label tables) is not
better: every design is within noise of a single pass or slightly worse on
topics, and costs 1-1.9x the output tokens plus 5-14x the uncached prompt
tokens and multi-turn latency. GLM does not actually interleave (it thinks
through the whole window, then submits once) and rarely uses a lookup tool.
Refine, a fixed second pass, remains the way to spend a second request.

**(d) What to drop.** Claims are the one component with a large, separable
cost: ~23% of output tokens on the benchmark, 14% on real traffic (+11%
throughput), and leaving them out hurts nothing else. Frames, evidence and
populations together are ~11% of output; narratives cost 18% of the prompt
but ~1% of output (cheap with prefix caching). Topic-only labeling is 28% cheaper on
real traffic (+23% throughput) and slightly better on topics. Within topics,
mental health and body systems draw the most thinking, but they are also most
of the content.

**Recommendation for a 100k-episode run on this hardware:** GLM-5.3-Flash
W4A16, served with the shared-prefix checkpoint, no speculation and
`--max-num-seqs 128` (raise it while KV stays below ~80%), high effort with an
8k-24k thinking budget and `max_tokens` capped near the budget plus ~16k;
~250-290 node-hours. Add refine on non-empty windows (~2x) if the quality gain
(+0.03-0.05 topic F1, +0.05 claims) is worth it, and consider moving claim
extraction to a separate pass if claims are needed only on some windows.


## (a) Throughput of each method

Node = 4x H100 80GB (gpu313), v8 prompt, real corpus windows (58% of them have
no health content). "Steady" is the rate between the 10th and 90th percentile
completions of a complete 1,500-window run, which is what a continuous
100k-episode stream sees; "wall" includes the run's tail. 100k episodes =
1.54M windows.

| method | windows / node-hour (steady; wall) | node-hours per 100k episodes | out tok/window | quality (v8 headline topic F1 / claim F1) |
| --- | --- | --- | --- | --- |
| keyword lexicon (CPU, 16 cores) | 0.6-6M per hour (11-100 windows/s/core) | <3 | - | ~0.34 topic F1 (v7) |
| TF-IDF screen (CPU) | millions | ~0 | - | screen only |
| Clef-flash screen (broad gate) | ~47k (13/s/GPU) | ~33 | - | screen only, passes 41-43% |
| DeepSeek-V4-Flash high, 24k budget | 4,250; 3,880 | 360-400 | 5.1k | 0.678 / 0.755 |
| DeepSeek-V4-Flash low | ~1.1x high (fixed horizon) | ~330-360 | | 0.715 v7 (vs 0.740 high) |
| **GLM-5.3-Flash high, 24k (G1 serving)** | **6,040; 5,300** | **255-290** | 2.2k | 0.709 / 0.783 (two runs) |
| GLM high, 8k budget | 6,280; 5,700 | 245-270 | 2.0k | 0.689 / 0.767 |
| GLM high, no claims | 6,690; 5,410 | 230-285 | 1.9k | 0.718 / - |
| GLM high, topics only | 7,450 | ~205 | 1.6k | 0.733 / - |
| GLM as first run (uncapped, no checkpoint) | ~1,500-2,100 (fixed horizon) | ~750-1,000 | | |
| Qwen3.8-Flash-Next xhigh (uncapped, recipe serving) | ~980 (fixed horizon, optimistic) | >1,500 | ~2.5x GLM | 0.705 / 0.794 |
| Qwen3.8-Flash-Next low (uncapped) | ~3,450 (fixed horizon, optimistic) | >450 | | 0.627 / 0.691 |
| GLM + GLM refine on non-empty windows | ~0.45x one GLM pass | ~560-640 | | 0.741 / 0.827 |
| GLM + Clef-flash screen in front | ~1.12x one GLM pass | ~230-260 + 33 | | loses ~1% of substantive content |

The refine and screen rows are derived (refine: second pass on the 42% of
windows the first pass labels, which are the expensive ones; on the benchmark
it costs ~1.05x a first pass on those windows); every other row is measured.
Screens save about their share of output tokens (~11% for both GLM and
DeepSeek: the 59% of windows a screen drops are the cheap ones), not their
share of windows.

## How throughput was measured

Real corpus windows, not benchmark items: a random pool of 4,000 windows from
`prod-sample-1000` (1,000 random episodes, 15.4 windows per episode, ~4.7k
characters per window; most windows have no health content). Two protocols:

- **Fixed horizon** (`exp/tprun.sh`): keep 512 requests in flight from the pool
  for 20 minutes, count completions between minutes 6 and 20, and read the
  server's own counters (generation and prefill tokens, running requests, KV
  use, preemptions, cache hits). Good for comparing serving configurations
  under identical load; it under-counts the longest windows (a 25k-token
  window takes longer than the horizon), so its absolute rate is optimistic.
- **Complete run** (`exp/fullrun.sh`): 1,500 random windows to completion,
  tail included. This is the number to plan with: windows per node-hour, and
  node-hours per 100k episodes (x 15.4 windows).

Quality numbers are the v8 headline items (160) scored against the v7 gold
through the label map, as in the first write-up.

## GLM-5.3-Flash serving on 4x H100

GLM-5.3-Flash is a hybrid: 34 linear-attention (KDA) layers and 11 sparse
(DSA/MLA) attention layers. On vLLM that has two consequences that dominate
throughput with an 87k-token shared prompt:

1. **Prefix caching runs in "align" mode** (attention blocks forced to 1,152
   tokens to match the linear-attention state page). A request can reuse the
   cached codebook only where a linear-attention state checkpoint exists.
   Without `--enable-mamba-shared-prefix-checkpoint`, under load the
   checkpoint at the end of the shared prefix is evicted and later requests
   re-prefill the codebook and hold their own copy of it; the server then fits
   ~30-60 requests and spends most of its time on prefill.
2. **Every running request holds a fixed block of linear-attention state**:
   ~12 pages (~14.7k token-equivalents of the 1.50M-token pool) with MTP-2
   speculative decoding, ~8.6k without speculation (and the pool grows to
   2.15M tokens without the MTP head). With thinking outputs of several
   thousand tokens on top, the pool holds ~60 requests (MTP) or ~100 (no
   spec), and the server preempts: a preempted request re-prefills its whole
   ~90k-token context. Preemption recompute was ~6-7k of the ~10k prefill
   tokens/s in every configuration below.

| config (v8, high effort, 24k budget) | windows/h (fixed horizon) | gen tok/s | prefill tok/s | running | preemptions/min | prompt cached |
| --- | --- | --- | --- | --- | --- | --- |
| A: as first run (MTP-2, prefix caching) | 2,100 | 1,750 | 8,400 | 44 | 3.0 | 82% |
| B2: + shared-prefix checkpoint, 4 API servers, async scheduling | 3,940 | 1,720 | 10,900 | 61 | 4.6 | 89% |
| C: checkpoint, no speculative decoding | 3,630 | 1,780 | 10,000 | 103 | 4.4 | 88% |
| E: B2 with max-num-seqs 96 | 3,940 | 1,700 | 10,400 | 65 | 4.6 | 89% |
| F: B2 + CPU KV offloading (400 GiB, native) | ~2,200 (stopped at 13 min) | 1,280 | 1,500 | 15 | 0 | 97% |
| G2: B2 capped at 48 sequences | 5,840 | 2,610 | 5,800 | 48 | 0 | 96% |
| **G1: checkpoint, no spec, capped at 128 sequences** | **7,480** | 3,450 | 5,100 | 128 | 0 | 97% |

- The shared-prefix checkpoint is the first flag that matters (+85%); the
  second is **capping concurrency below the point where KV saturates**
  (`--max-num-seqs`): no preemption, the shared prefix stays cached, prefill
  falls to ~3.5k tokens a window, and throughput rises another 50-90%.
  Without the cap, a saturated KV pool evicts the shared-prefix checkpoint,
  later requests miss the cache entirely and hold private copies of the
  87k-token prompt, and the server spirals down (on the heavier benchmark
  windows it fell to 17 running requests and ~260 windows/h until capped).
- MTP-2 and no speculation tie: MTP makes each sequence faster (acceptance
  ~0.69, ~2.4 tokens per step) but costs a third of the KV pool and half the
  concurrent requests.
- A cap of 96 with MTP changed nothing because KV saturated at ~60 requests
  first; the cap has to sit below the saturation point (48 with MTP-2, 128
  without speculation, at the corpus mix; lower for health-dense traffic).
- **Complete run, G1 config** (1,500 random corpus windows, tail included):
  17.0 minutes, 5,300 windows/h wall-clock and 6,040/h between the 10th and
  90th percentile completions; 2.18k output tokens per window on average
  (median 384, p95 10.4k). The fixed-horizon number (7,480) overstates by ~25%
  because the longest windows outlast the horizon. **One v8 pass over 100k
  episodes (1.54M windows) is ~255-290 node-hours on this node.**
- Without speculation the per-request state is smaller and the pool larger,
  so the capped no-spec server runs 128 requests against MTP's 48, and wins
  despite slower individual sequences.
- CPU KV offloading removes preemption recompute (prefill falls from 10.4k to
  1.5k tok/s, 97% of prompt tokens cached) but halves throughput: requests
  restored from CPU hold their own GPU copy of the shared 87k-token prefix
  instead of sharing it, so only ~15 fit. It would help a workload without a
  long shared prefix; it does not help this one.

### Request variants on real traffic (G1 server, complete runs of 1,500 windows)

| variant | out tok/w (mean / p95) | windows/h steady (10-90%) | windows/h wall | vs high |
| --- | --- | --- | --- | --- |
| high, 24k budget | 2,180 / 10.4k | 6,040 | 5,300 | - |
| high, 8k budget | 2,000 / 9.8k | 6,280 | 5,700 | +4% steady |
| no claims | 1,880 / 8.5k | 6,690 | 5,410 | +11% steady |
| topics only | 1,580 / 6.5k | 7,450 | 3,950* | +23% steady |

\* Two of the 1,500 topic-only windows ran away to the 80,000-token
`max_tokens` limit (the answer looped after thinking ended), holding a slot
for ~50 minutes each and setting the wall-clock end. Runaway answers happen in
~0.1-0.3% of GLM windows across runs (also 1 of 321 in the first GLM run);
production requests should cap `max_tokens` near the thinking budget plus
~16k and retry a truncated answer. The fixed-horizon throughput runs of the
same variants were all within 2% of each other (and topic-only, hit by one of
the runaways early, came out lower), because a 20-minute horizon hardly sees
the long windows where these variants save tokens; complete runs are the
measure to use for request-level changes.

On real traffic the savings are smaller than on the benchmark because 58% of
windows have no health content and cost little either way, and per-window
fixed costs (prefill of the window and the uncached prompt tail, ~3.5k tokens;
a slot in a capped server) do not shrink.

### Other GLM serving options from the model card and recipes

- **DFlash2-G drafter** (`canada-quant/GLM-5.3-Flash-DFlash2-G`, K=4): does not
  load on upstream vLLM nightly ("Model does not support EAGLE3 interface");
  the card's x86 numbers come from a patched image
  (`ghcr.io/canada-quant/vllm-glm53-flash-h100:v2-w4a16-dflash2`). Not tried
  further: the card itself says TP4 with the drafter cuts the KV pool ~6x
  (eight full-attention drafter layers caching the whole context), caps
  context at 131k with any drafter, and recommends the built-in MTP head for
  long contexts. KV capacity is exactly what limits this workload, and the
  measurements above show even MTP's smaller state costs more than it gains.
- **NVFP4** (NVIDIA's checkpoint): Hopper has no FP4 units, so every weight goes
  through emulation kernels; the canada-quant comparison on 4x H100 has W4A16
  ahead at c32 (1,161 vs 771 tok/s) and level elsewhere. Not run.
- **fp8 KV cache**: not available on Hopper for this NoPE model (model card;
  the vLLM recipe uses fp8 KV only on Blackwell/Instinct).
- **Prefix caching on** (the card's H200 recipe turns it off): with an 87k-token
  shared prompt, off would mean re-prefilling 87k tokens per window.
- **Two TP2 replicas** (the card's advice on 8x H200): the W4A16 weights
  (178 GB) do not fit in 2x 80 GB.
- **DeepSeek-V4-Flash with its MTP layer**: vLLM 0.29 fails to load the MTP
  weights (`KeyError: model.layers.43.mtp_block.main_norm.weight`); untested.

## Qwen3.8-Flash-Next

`Qwen/Qwen3.8-Flash-Next-FP8` (125B total, 6B active, plus a 51B n-gram
embedding table that vLLM keeps in CPU memory on H100; 36 Gated-DeltaNet and 12
full-attention layers; MTP), served per the vLLM recipe for 4x H100: TP4,
`--moe-backend triton`, MTP-3, `qwen3` reasoning parser, prefix caching with the
shared-prefix checkpoint. KV pool 2.0M tokens (800-token blocks). Its template
accepts `reasoning_effort` xhigh (default), medium or low (not "high").

| run (v8 headline, mapped) | topic P | topic R | topic F1 | parent F1 | narr F1 | frame F1 | evid F1 | pop F1 | claim F1 | prod F1 | out tok/w | think tok/w |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GLM-5.3-Flash high | 0.810 | 0.602 | 0.703 | 0.757 | 0.680 | 0.752 | 0.618 | 0.764 | 0.770 | 0.811 | 6.7k | 5.1k |
| DeepSeek-V4-Flash high | 0.820 | 0.562 | 0.678 | 0.714 | 0.676 | 0.749 | 0.657 | 0.760 | 0.755 | 0.859 | 13.1k | 11.5k |
| Qwen3.8-Flash-Next xhigh | 0.690 | 0.701 | 0.705 | 0.750 | 0.638 | 0.713 | 0.693 | 0.743 | 0.794 | 0.862 | 15.6k | 12.8k |
| Qwen3.8-Flash-Next medium | 0.829 | 0.501 | 0.639 | 0.679 | 0.643 | 0.694 | 0.639 | 0.744 | 0.720 | 0.806 | 6.4k | 5.0k |
| Qwen3.8-Flash-Next low | 0.855 | 0.478 | 0.627 | 0.678 | 0.569 | 0.699 | 0.613 | 0.624 | 0.691 | 0.771 | 5.4k | 4.1k |
| GLM high ∪ Qwen xhigh | 0.729 | 0.744 | 0.746 | 0.750 | 0.735 | 0.780 | 0.716 | 0.784 | 0.822 | 0.830 | 22.3k | |
| GLM + GLM refine (first write-up) | 0.800 | 0.673 | 0.741 | 0.796 | 0.687 | 0.788 | 0.686 | 0.787 | 0.827 | 0.849 | 13.8k | |

At xhigh, Qwen3.8 ties GLM on topics with a very different error profile
(recall 0.70, precision 0.69: it labels more, including more that the gold
does not), has the best single-pass claim F1 measured (0.794), and is weaker
on narratives. It thinks 2.5x as long as GLM, and on real windows it ran at
~980 windows/h against ~3,900 for GLM served the same way (uncapped; fixed horizon; 135 preemptions in 20
minutes, MTP-3 acceptance 0.45). At low effort it is cheaper than GLM but
clearly worse, and at medium it spends what GLM high spends (6.4k tokens a
window) for much less (topic F1 0.639 vs 0.709, claims 0.720 vs 0.783). Its union with GLM ties GLM + GLM refine on topics and claims
and has the best narrative F1 of any GLM-based configuration (0.735), at
~1.6x refine's tokens (22.3k vs 13.8k a window); it is a quality option, not a throughput one. Qwen was
served per the vLLM recipe (256 sequences, MTP-3) and preempted heavily
(135-209 preemptions in 20 minutes); a concurrency cap would likely help it as
it helped GLM, but at the efforts where it would be fast (low, medium) its
quality is below GLM high at the same token cost, so this was not pursued.

## (b) GLM-5.3-Flash: reasoning level, budget, prompt, thinking off

GLM-5.3's chat template takes `reasoning_effort` low, high or max (anything
else, including omitting it, means max) and writes "Reasoning Effort: X" as
the first system line, so runs at different levels do not share a prompt
prefix. The thinking budget (vLLM `thinking_token_budget`) works with the
`glm45` reasoning parser. All runs below: v8 headline items (160), one pass,
scored on the v7 gold through the label map; paired deltas are against the
first GLM run (high, 24k budget).

| run | topic P | topic R | topic F1 | parent F1 | narr F1 | frame F1 | evid F1 | pop F1 | claim F1 | prod F1 | out tok/w | think tok/w |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high, 24k budget (first run) | 0.810 | 0.602 | 0.703 | 0.757 | 0.680 | 0.752 | 0.618 | 0.764 | 0.770 | 0.811 | 6.7k | 5.1k |
| max, 24k budget | 0.787 | 0.639 | 0.718 | 0.771 | 0.725 | 0.759 | 0.679 | 0.788 | 0.817 | 0.847 | 15.2k | 13.4k |
| high, 8k budget | 0.815 | 0.577 | 0.689 | 0.733 | 0.671 | 0.725 | 0.601 | 0.667 | 0.767 | 0.813 | 5.4k | 3.8k |
| high, 4k budget | 0.793 | 0.542 | 0.654 | 0.709 | 0.644 | 0.691 | 0.564 | 0.602 | 0.713 | 0.802 | 3.7k | 2.2k |
| low, 24k budget | 0.803 | 0.526 | 0.647 | 0.703 | 0.593 | 0.665 | 0.523 | 0.631 | 0.692 | 0.768 | 2.4k | 1.1k |

- **max** buys evidence (+0.060 [0.008, 0.109]) and claim recall (+0.062
  [-0.008, 0.129]); topic F1 +0.015 is within noise. It costs 2.3x the tokens.
- **high with an 8k budget** is within noise of high/24k on everything but
  populations (-0.098 [-0.170, -0.035]), with 20% fewer tokens and slightly
  higher claim precision.
- **4k budget and low effort** lose significantly on every axis (low: topic
  -0.056 [-0.082, -0.028], claim recall -0.116).

**Run-to-run noise.** A second high/24k run differs from the first by topic
+0.011, claims +0.025, products +0.043, populations -0.033, and the item
bootstrap calls the claim-precision (+0.031) and product (+0.043) differences
"significant": single-run differences below ~0.03-0.04 are not evidence, and
the item-level intervals understate the uncertainty for one-pass runs. Two runs
averaged: topic F1 0.709, claim F1 0.783, populations 0.748, evidence 0.611.

| run | topic P | topic R | topic F1 | parent F1 | narr F1 | frame F1 | evid F1 | pop F1 | claim F1 | prod F1 | out tok/w | think tok/w |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high, 24k budget, repeat | 0.820 | 0.613 | 0.714 | 0.770 | 0.683 | 0.749 | 0.604 | 0.732 | 0.795 | 0.855 | 6.5k | 4.8k |
| high + "think efficiently" note | 0.827 | 0.598 | 0.708 | 0.762 | 0.696 | 0.734 | 0.663 | 0.694 | 0.796 | 0.853 | 6.4k | 4.7k |
| thinking off | 0.739 | 0.415 | 0.549 | 0.606 | 0.496 | 0.493 | 0.347 | 0.364 | 0.594 | 0.679 | 1.6k | - |

- **A system-prompt note asking for efficient thinking** (`exp/note-efficient.md`:
  decide empty windows quickly, don't restate the codebook, decide each label
  once) changes nothing measurable: -6% tokens, every axis within run noise
  except populations (-0.070).
- **Thinking off** (a per-request chat template whose generation prompt closes
  an empty think block) is fast (1.6k tokens a window, all of it the answer)
  and poor: topic F1 0.549, populations 0.364, evidence 0.347. It needs the
  answer without structured output (the `glm45` parser files everything as
  reasoning and a grammar applied there garbles the keys), and 2% of answers
  were not JSON on the first try.

## (c) Tool-based labeling

`exp/toollabel.py`, GLM-5.3-Flash high/24k (per turn), v8 headline, with
reasoning passed back each turn (`reasoning_content`) so thinking is
continuous across tool calls (GLM's template keeps it for turns after the
last user message). Three designs:

- **incremental**: `add_detections`, `add_claims`, `add_products` (lists, each
  item checked against the codebook's mechanical rules and answered with
  what was accepted and why anything was rejected), then `finish`; the prompt
  asks the model to record annotations stretch by stretch as it reads.
- **submit**: one `submit_annotation` call with the whole result, answered with
  every violation; the model may resubmit (up to 3) or `finish`.
- **lookup**: submit, but the system prompt carries only a label index (IDs and
  names: 43k tokens instead of 86k) and `lookup_labels` returns definitions,
  boundary notes and examples for label IDs, parents or narrative families.

| run | topic F1 | parent F1 | narr F1 | frame F1 | evid F1 | pop F1 | claim F1 | prod F1 | out tok/w | turns | prompt tok/w (uncached) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single pass (two runs) | 0.709 | 0.764 | 0.682 | 0.751 | 0.611 | 0.748 | 0.783 | 0.833 | 6.6k | 1 | 88k (~2.4k) |
| incremental | 0.686 | 0.742 | 0.702 | 0.749 | 0.642 | 0.661 | 0.807 | 0.818 | 6.7k | 2.1 | 198k (12k) |
| submit | 0.697 | 0.734 | 0.705 | 0.721 | 0.638 | 0.672 | 0.762 | 0.798 | 11.0k | 3.0 | 286k (32k) |
| lookup | 0.689 | 0.748 | 0.733 | 0.728 | 0.659 | 0.694 | 0.774 | 0.829 | 12.4k | 3.6 | 200k (33k) |
| single pass + refine (first write-up) | 0.741 | 0.796 | 0.687 | 0.788 | 0.686 | 0.787 | 0.827 | 0.849 | 13.8k | 2 | |

Against both single-pass runs, every tool design is slightly worse on topics
(-0.006 to -0.028) and on populations, and slightly better on narratives
(+0.02 to +0.05) and evidence (+0.02 to +0.055); only lookup's evidence gain
and incremental's topic loss clear the item-level intervals against both, and
both are near the run-to-run noise. None comes near refine.

How the model used the tools explains why:

- **It does not interleave.** In incremental mode it averaged 2.1 turns: it
  thought through the whole window, then made one `add_detections`, one
  `add_claims` and `finish`. Asked to work stretch by stretch, it front-loads
  the thinking anyway, so incremental is a single pass with an extra round
  trip.
- **It rarely looks things up.** In lookup mode it called `lookup_labels` 0.75
  times a window and chose most labels from the names alone; the shorter
  prompt was paid back with more thinking (12.4k output tokens a window).
- **The feedback fixes what lenient validation already fixes.** Most messages
  were quote repairs; the substantive rejections were required fields left
  out of tool arguments (`claim_type`, `expressed_certainty`, unit IDs; tool
  arguments are not schema-constrained the way the structured final answer
  is), which resubmission partly recovers.
- **It is expensive to serve.** Every turn re-sends the conversation (200-286k
  prompt tokens a window, 12-33k of them uncached against ~2.4k for one pass),
  the multi-turn state holds KV between turns, and on a saturated batch
  server each turn goes to the back of the queue: before switching to
  priority scheduling (later turns first, `--scheduling-policy priority`),
  conversations took 20+ minutes each.

A version that could pay off is one that keeps the single structured pass and
uses tools only where they add information the model lacks: a second turn only
for windows whose answer failed validation (rare), or refine framed as a tool
("here is your first pass; add what is missing"), which is what refine already
is. Lookup would make sense only with a model that actually consults it, or if
the full label tables were too long to serve at all.

## (d) What each part of the label set costs

Two views. **Correlational** (`exp/costparts.py`): split every window's output
into thinking and answer tokens, the answer by section, and regress thinking
tokens on per-window label counts (non-negative least squares). **Causal**:
ablation runs that leave a component out of the prompt, the schema and the
output (`exp/variants.py`, `--drop`), scored on what remains.

Where GLM's output goes (v8, 600 real corpus windows): thinking is 77% of
output tokens (DeepSeek 91%); windows with no health content (42%) take 2%
of all output tokens. Of the answer itself, claims are 44%, topic detections
32%, evidence 9%, frames 6%, products, narratives and populations ~2% each.
The regression attributes ~26% of thinking to claims (+370 thinking tokens per
claim), ~10% to the mind/mental-health topics, ~9% to body systems and
chronic conditions, 7% to frames, 5% each to evidence and populations
(the benchmark run and DeepSeek's corpus run give the same ordering).

Prompt tokens by component (85.6k total): topic tables ~37k, narratives 15.1k
(section 5.2 plus their table), frames 4.0k, claims 3.5k, evidence 3.1k,
populations 1.5k, products 1.4k; the rest is the rubric, ground rules and
boundary tests.

Ablations (GLM high/24k, v8 headline; deltas against the repeat run, which
has the same server and settings):

| left out | prompt tokens | out tok/w | change in tokens | remaining axes |
| --- | --- | --- | --- | --- |
| nothing (two runs) | 85.6k | 6.6k | - | topic 0.709, claims 0.783 |
| claims | 82.2k | 5.1k | -23% | all within noise; evidence +0.077 [0.030, 0.128] |
| frames, evidence, populations | 77.1k | 5.9k | -11% | all within noise |
| narratives | 70.6k | 6.5k | -1% | all within noise (claim precision -0.030) |
| everything but topics | 57.2k | 4.2k | -36% | topic recall +0.051 [0.023, 0.082], F1 +0.019 |

- **Claims are the one component with a large, separable cost**: ~23% of
  output tokens, and leaving them out does not hurt anything else (evidence
  detections even improve). If claim extraction is needed only for a subset
  (e.g. windows with narratives, or a later verification stage), running it
  as a separate pass on the windows that need it is the obvious saving.
- **Narratives cost prompt, not output**: 15k prompt tokens (18% of the
  prompt) but ~1% of output. On GLM the prompt is shared and cached, so they
  are nearly free per window; they matter on models without long-prefix
  sharing and for preemption recompute.
- **Frames, evidence and populations** together are ~11% of output tokens.
  Populations are the noisiest axis run to run (±0.03-0.10).
- **Topic-only labeling** is 36% cheaper and slightly better on topics; the
  other axes cost little individually but add up.
- Within topics, the mental-health and body-systems domains draw the most
  thinking per label; they are also the bulk of the health content, so this
  is not a case for dropping them (see the first write-up for the v8 boundary
  rules that already trimmed loose psychiatric and crime/death talk).

## Caveats

- Quality is the v8 headline (160 items) scored on the v7 gold through the
  label map, one run per configuration (two for GLM high); single-run
  differences under ~0.03-0.04 are noise. v8 numbers rank methods; they are
  not v8 quality.
- Throughput is one node, one workload (the v8 87k-token prompt, real
  windows from 1,000 random episodes). Fixed-horizon runs compare serving
  configurations but overstate absolute rates by ~25% (GLM) or more
  (DeepSeek, whose long windows are longer); plan with complete runs.
- DeepSeek's serving was not re-tuned here (512 sequences, fp8 KV; it ran at
  ~85% KV with few preemptions); GLM's was. The GLM-vs-DeepSeek ratio is for
  the configurations as measured.
- The tool-mode harness fills omitted empty arrays and drops unknown keys in
  tool arguments before validating (a first version without this rejected
  most claims; those runs are kept as `*-v1`).
- The Qwen and DeepSeek MTP / DFlash results are limited by what this
  node's software stack could run (driver 570, upstream vLLM).

## Reproducing

```bash
# GLM server configs (exp/serve-glm.sh; env TAG, SPEC, SEQS, EXTRA)
TAG=G1 SPEC=none SEQS=128 EXTRA="--enable-mamba-shared-prefix-checkpoint --api-server-count 4 --async-scheduling --trust-request-chat-template" exp/serve-glm.sh
# throughput: fixed horizon (20 min) and complete run (1,500 windows)
CONC=384 exp/tprun.sh glm-G1-nospec-seq128 20
CONC=384 exp/fullrun.sh glm-high [--budget 8000 | --drop claims | --note-file exp/note-efficient.md]
.venv/bin/python exp/tpstats.py exp/full/glm-high [--window 6 20 for tprun dirs]
# quality variants (v8 headline) and scoring against the v7 gold
.venv/bin/python exp/xlabel.py --bench v3 --name v8g-max --model glm53-w4 --strata health_dense mixed null ad_read discourse --effort max
.venv/bin/python exp/xlabel.py ... --drop claims,products,narrative,frame,evidence,population
.venv/bin/python exp/xlabel.py ... --effort low --prefill-nothink
.venv/bin/python exp/toollabel.py --bench v3 --mode incremental|submit|lookup --name v8g-tool-inc --priority ...
BENCHMARK_DIR=benchmark/v2 .venv/bin/python -m analysis.benchmark score --alias exp/alias-v8-to-v7.json benchmark/v3/runs/v8g-max
.venv/bin/python exp/summarize.py benchmark/v3/runs/v8g-*
# cost attribution
.venv/bin/python exp/costparts.py --bench v3 exp/corpus/v8-glm
# KV footprint probe
.venv/bin/python exp/kvprobe2.py v3 glm53-w4 1,4,16 512
# Qwen3.8 and DeepSeek
TAG=q1 EXTRA="--enable-mamba-shared-prefix-checkpoint --api-server-count 4" exp/serve-qwen38.sh
TAG=ds1 exp/serve-ds.sh
```
