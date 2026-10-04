"""A local TypeSafe-compatible ``/v1/systemone`` endpoint for Cloudflare's Clef models.

Clef and Clef-flash (https://huggingface.co/Cloudflare/clef) are open-weight
decision models with the same request and response bodies as TypeSafe's Jev,
so ``label --api typesafe`` and the benchmark runner use them unchanged when
``api_base`` points here. One process serves one model on one GPU; start one
per GPU and list them all in ``api_base`` to spread windows across them.

    CUDA_VISIBLE_DEVICES=0 .venv/bin/python -m analysis.serving.clef_server \
        --model clef-flash --port 8301

What this adds over the model card's ``systemone`` function:

- **No silent truncation.** The release's ``encode_record`` cuts the *state* to
  fit ``max_length`` without a word, which for a labeling request means judging
  passages the model never saw. Here a request too long for one forward pass is
  split into several passes over the whole state, each holding as many
  questions as fit, and a state that cannot fit with even one question is a 400.
- **Batching.** Concurrent short requests (window screens, attribute requests)
  are padded into one forward pass up to a token budget; long ones run alone,
  where a single sequence already saturates the GPU.
- **No processor.** Only the tokenizer is loaded: the video processor needs
  torchvision and text requests never touch it.

Clef decides the questions of one pass jointly (the schema head attends across
fields), unlike Jev, whose questions are answered independently. Splitting a
request therefore changes which questions see each other. ``--max-questions``
bounds the questions per pass so that this can be studied rather than left to
the token budget. The split is deterministic: the fewest passes, near-equal in
size, in request order.
"""

from __future__ import annotations

import argparse
import json
import math
import queue
import sys
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import torch

MODELS = {"clef": "Cloudflare/clef", "clef-flash": "Cloudflare/clef-flash"}
# Clef is trained to 64k tokens of context.
DEFAULT_MAX_TOKENS = 65_536


def load(model_name: str, device: str = "cuda") -> tuple[Any, Any, Any]:
    """(model, tokenizer, release module) for a Clef release."""
    from huggingface_hub import snapshot_download
    from safetensors.torch import load_file
    from transformers import AutoTokenizer, Qwen3_5ForConditionalGeneration

    path = Path(snapshot_download(MODELS.get(model_name, model_name)))
    sys.path.insert(0, str(path))
    import joint_schema_model as release  # the model card's own code

    backbone = Qwen3_5ForConditionalGeneration.from_pretrained(
        path, dtype=torch.bfloat16, device_map={"": device}
    )
    backbone.config.use_cache = False
    head = release.JointSchemaHead(**json.loads((path / "joint_head_config.json").read_text()))
    head.load_state_dict(load_file(path / "joint_head.safetensors"), strict=True)
    model = release.ClefModel(backbone, head.to(device=device, dtype=torch.bfloat16)).eval()
    return model, AutoTokenizer.from_pretrained(path), release


class RequestError(ValueError):
    """A request this server will not answer (HTTP 400)."""


@dataclass
class Pass:
    """One forward pass: a whole request, or one slice of its questions."""

    encoded: Any
    questions: dict[str, Any]
    done: threading.Event = field(default_factory=threading.Event)
    answers: dict[str, Any] | None = None
    error: BaseException | None = None


class ClefServer:
    def __init__(
        self,
        model_name: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        max_questions: int | None = None,
        batch_tokens: int = 32_768,
        max_batch: int = 16,
    ) -> None:
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.max_questions = max_questions
        self.batch_tokens = batch_tokens
        self.max_batch = max_batch
        self.model, self.tokenizer, self.release = load(model_name)
        self.device = next(self.model.parameters()).device
        self.queue: queue.Queue[Pass] = queue.Queue()
        # A pass taken off the queue that did not fit the batch being built.
        self._carry: Pass | None = None
        self.stats = {"requests": 0, "passes": 0, "forwards": 0, "tokens": 0, "gpu_seconds": 0.0}
        self.lock = threading.Lock()
        threading.Thread(target=self._worker, daemon=True).start()

    def warm_up(self) -> None:
        """Run one pass per sequence-length bucket and batch shape.

        The linear-attention kernels autotune the first time they see a new
        length bucket, about ten seconds each on an H100. Paying that while
        serving puts ten-second stalls into the first windows of every run.
        With TRITON_CACHE_AUTOTUNING=1 the results persist across restarts.
        """
        filler = "word " * self.max_tokens
        shapes = []
        length = 1024
        while length < self.max_tokens:
            shapes.append((1, length))
            length *= 2
        shapes.append((1, self.max_tokens - 64))
        # Some kernels key their tuning on the batch size itself, so every size
        # a batch can take is one more tuning run; length buckets matter less.
        for size in range(2, self.max_batch + 1):
            length = 1024
            while size * length <= self.batch_tokens:
                shapes.append((size, length))
                length *= 4
        question = {"q": {"type": "noul", "instructions": "Is this text about health?"}}
        for size, length in shapes:
            ids = self.tokenizer(filler, add_special_tokens=False).input_ids[: length - 64]
            state = self.tokenizer.decode(ids)
            encoded = [self.release.encode_record(self.tokenizer, {"state": state, "questions": question},
                                                  max_length=self.max_tokens)] * size
            started = time.monotonic()
            with torch.inference_mode():
                self.model(self.release.collate_records(encoded, self.tokenizer.pad_token_id, self.device))
            torch.cuda.synchronize()
            print(f"warm-up batch {size} x {len(encoded[0].input_ids)} tokens: "
                  f"{time.monotonic() - started:.1f}s", flush=True)

    # -- encoding -------------------------------------------------------------

    def _encode(self, state: Any, questions: dict[str, Any]) -> Any:
        record = {"state": state, "questions": questions}
        try:
            encoded = self.release.encode_record(self.tokenizer, record, max_length=self.max_tokens)
        except ValueError as exc:  # the schema alone is over the limit
            raise _Overflow(str(exc)) from exc
        # encode_record truncates the state to make room; a full-length record
        # is one that may have been cut, and is never accepted.
        if len(encoded.input_ids) >= self.max_tokens:
            raise _Overflow("state and questions exceed the context")
        return encoded

    def plan(self, state: Any, questions: dict[str, Any]) -> list[Pass]:
        """Split ``questions`` into the fewest passes that each fit, in order."""
        items = list(questions.items())
        cap = self.max_questions or len(items)
        parts = max(1, math.ceil(len(items) / cap))
        while True:
            size = math.ceil(len(items) / parts)
            chunks = [dict(items[start : start + size]) for start in range(0, len(items), size)]
            try:
                return [Pass(self._encode(state, chunk), chunk) for chunk in chunks]
            except _Overflow:
                if size == 1:
                    raise RequestError(
                        "the state does not fit in the context with even one question"
                    ) from None
                parts += 1

    # -- the GPU worker -------------------------------------------------------

    def _take_batch(self) -> list[Pass]:
        batch = [self._carry if self._carry is not None else self.queue.get()]
        self._carry = None
        longest = len(batch[0].encoded.input_ids)
        while len(batch) < self.max_batch:
            try:
                candidate = self.queue.get_nowait()
            except queue.Empty:
                break
            length = max(longest, len(candidate.encoded.input_ids))
            if length * (len(batch) + 1) > self.batch_tokens:
                # Over budget: it leads the next batch, ahead of anything queued after it.
                self._carry = candidate
                break
            batch.append(candidate)
            longest = length
        return batch

    def _worker(self) -> None:
        pad = self.tokenizer.pad_token_id
        while True:
            batch = self._take_batch()
            started = time.monotonic()
            try:
                collated = self.release.collate_records([item.encoded for item in batch], pad, self.device)
                with torch.inference_mode():
                    logits = self.model(collated)
                for item, record_logits in zip(batch, logits):
                    item.answers = {
                        question.question_id: self.release.systemone_answer(
                            item.questions[question.question_id],
                            dict(zip(question.option_ids, question_logits.float().softmax(-1).tolist())),
                        )
                        for question, question_logits in zip(item.encoded.questions, record_logits)
                    }
            except BaseException as exc:  # noqa: BLE001 -- reported to every waiter
                for item in batch:
                    item.error = exc
                if isinstance(exc, torch.cuda.OutOfMemoryError):
                    torch.cuda.empty_cache()
            finally:
                with self.lock:
                    self.stats["forwards"] += 1
                    self.stats["passes"] += len(batch)
                    self.stats["tokens"] += sum(len(item.encoded.input_ids) for item in batch)
                    self.stats["gpu_seconds"] += time.monotonic() - started
                for item in batch:
                    item.done.set()

    # -- the API --------------------------------------------------------------

    def systemone(self, request: dict[str, Any]) -> dict[str, Any]:
        questions = request.get("questions")
        if request.get("model") not in (None, self.model_name):
            raise RequestError(f"this endpoint serves {self.model_name}, not {request.get('model')}")
        if "state" not in request:
            raise RequestError("state is required")
        if not isinstance(questions, dict) or not questions:
            raise RequestError("at least one question is required")
        for question_id, question in questions.items():
            if not isinstance(question, dict) or question.get("type") not in self.release.QUESTION_TYPES:
                raise RequestError(f"{question_id}: type must be noul, choice, or score")
            if question["type"] != "noul" and not question.get("criteria"):
                raise RequestError(f"{question_id}: criteria must not be empty")
        passes = self.plan(request["state"], questions)
        for item in passes:
            self.queue.put(item)
        answers: dict[str, Any] = {}
        for item in passes:
            item.done.wait()
            if item.error is not None:
                raise item.error
            answers.update(item.answers or {})
        with self.lock:
            self.stats["requests"] += 1
        return {
            "model": self.model_name,
            # In request order, as the client sent them.
            "answers": {question_id: answers[question_id] for question_id in questions},
            "usage": {
                "input_tokens": sum(len(item.encoded.input_ids) for item in passes),
                "output_tokens": 0,
                "passes": len(passes),
            },
        }


class _Overflow(Exception):
    pass


def make_handler(server: ClefServer) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _send(self, status: int, body: dict[str, Any]) -> None:
            data = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.rstrip("/") == "/v1/models":
                self._send(200, {"models": [{"name": server.model_name}]})
            elif self.path.rstrip("/") == "/stats":
                with server.lock:
                    self._send(200, {**server.stats, "queued": server.queue.qsize()})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path.rstrip("/") != "/v1/systemone":
                self._send(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
                request = json.loads(self.rfile.read(length))
                self._send(200, server.systemone(request))
            except (RequestError, json.JSONDecodeError) as exc:
                self._send(400, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                self._send(500, {"error": f"{type(exc).__name__}: {exc}"[:500]})

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--model", default="clef-flash", help="clef, clef-flash, or a local path")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8301)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
                        help="longest single forward pass, in tokens")
    parser.add_argument("--max-questions", type=int, default=None,
                        help="most questions decided jointly in one pass (default: as many as fit)")
    parser.add_argument("--batch-tokens", type=int, default=32_768,
                        help="padded tokens per batched forward pass")
    parser.add_argument("--max-batch", type=int, default=16)
    parser.add_argument("--no-warm-up", action="store_true",
                        help="skip compiling the kernels for every length bucket before serving")
    args = parser.parse_args()
    server = ClefServer(args.model, args.max_tokens, args.max_questions, args.batch_tokens, args.max_batch)
    if not args.no_warm_up:
        server.warm_up()
    httpd = ThreadingHTTPServer((args.host, args.port), make_handler(server))
    httpd.daemon_threads = True
    print(f"serving {args.model} on http://{args.host}:{args.port}/v1/systemone", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
