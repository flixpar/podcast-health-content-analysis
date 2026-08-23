"""Logging setup shared by every command."""

from __future__ import annotations

import logging
from pathlib import Path

FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def configure_logging(log_file: Path | None = None, level: str = "INFO") -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(level=getattr(logging, level.upper()), format=FORMAT,
                        handlers=handlers, force=True)
    # Retried requests and NeMo's own startup chatter drown out the pipeline's log.
    for noisy in ("urllib3", "nemo_logger", "nemo", "filelock", "huggingface_hub"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
