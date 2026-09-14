"""vLLM reasoning-parser plugin: parser-engine adapters with an O(delta) reasoning-end check.

Load with ``--reasoning-parser-plugin <this file>`` and pick one of the parsers it
registers: ``deepseek_v4_fast``, ``qwen3_fast``, ``gemma4_fast`` -- the same
parsers as ``deepseek_v4``, ``qwen3`` and ``gemma4`` apart from that one check.

Why: in vLLM 0.29 (g4cf572b6e) the parser-engine reasoning adapters built by
``make_adapters`` do not override ``is_reasoning_end_streaming``, so the base
class falls back to ``is_reasoning_end(all_token_ids)``. For every
structured-output request that is still thinking, on every decode step, that
copies the request's whole token list (prompt plus output, tens of thousands of
ids) and scans it backwards to the think-start token. Measured on DeepSeek-V4
at 64 concurrent labeling requests, that loop was 92% of EngineCore time; the
GPUs sat at ~35% utilisation and aggregate decode fell as outputs grew. With
this plugin the same load decodes 1.8x faster at short outputs with the GPUs
at 100%.

The structured-output manager only asks while ``reasoning_ended`` is still
False (it settles the prompt with a full ``is_reasoning_end`` once), so the
state can only change inside this step's new tokens. Scanning just the delta,
with the same precedence as the full scan (latest end / start / turn boundary
wins), gives the same answer.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from vllm.parser.engine.parser_engine_config import ParserState
from vllm.parser.engine.registered_adapters import (
    DeepSeekV4ParserReasoningAdapter,
    Gemma4ParserReasoningAdapter,
    Qwen3ParserReasoningAdapter,
)
from vllm.reasoning import ReasoningParserManager


class DeltaReasoningEndMixin:
    def is_reasoning_end_streaming(
        self, input_ids: Sequence[int], delta_ids: Iterable[int]
    ) -> bool:
        engine = self._parser_engine
        end_id = engine._reasoning_end_token_id
        if end_id is None:
            return super().is_reasoning_end_streaming(input_ids, delta_ids)
        # Only sound while callers ask solely before reasoning has ended (see
        # StructuredOutputManager.should_advance). Recheck after a vLLM upgrade.
        start_id = engine._reasoning_start_token_id
        boundary_ids = engine._turn_boundary_token_ids
        for token_id in reversed(list(delta_ids)):
            if token_id == end_id:
                return True
            if start_id is not None and token_id == start_id:
                return False
            if token_id in boundary_ids:
                return engine.parser_engine_config.initial_state != ParserState.REASONING
        return False


@ReasoningParserManager.register_module("deepseek_v4_fast")
class DeepSeekV4FastReasoningAdapter(DeltaReasoningEndMixin, DeepSeekV4ParserReasoningAdapter):
    pass


@ReasoningParserManager.register_module("qwen3_fast")
class Qwen3FastReasoningAdapter(DeltaReasoningEndMixin, Qwen3ParserReasoningAdapter):
    pass


@ReasoningParserManager.register_module("gemma4_fast")
class Gemma4FastReasoningAdapter(DeltaReasoningEndMixin, Gemma4ParserReasoningAdapter):
    pass
