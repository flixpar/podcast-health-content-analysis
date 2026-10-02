"""``python -m podcast_pipeline study <action>``."""

from __future__ import annotations

import argparse
import json
import sqlite3

from podcast_pipeline.config import Config
from podcast_pipeline.studies import REGISTRY, get
from podcast_pipeline.studies.export import export
from podcast_pipeline.studies.materialize import refresh
from podcast_pipeline.studies.status import status


def dispatch(args: argparse.Namespace, config: Config, conn: sqlite3.Connection) -> dict:
    match args.study_command:
        case "list":
            stored = {r["name"]: r for r in conn.execute("SELECT * FROM studies")}
            return {"studies": [{
                "name": name,
                "description": cls.description,
                "revision": stored[name]["revision"] if name in stored else None,
                "refreshed_at": stored[name]["refreshed_at"] if name in stored else None,
                "definition_current": (stored[name]["definition_hash"] == cls().definition_hash()
                                       if name in stored else None),
                "last_refresh": json.loads(stored[name]["summary"] or "{}") if name in stored else None,
            } for name, cls in sorted(REGISTRY.items())]}
        case "refresh":
            # Each study refreshes on its own: one that cannot (no chart data
            # yet) must not leave the others unmaterialized. Failures are
            # raised after the rest have run.
            names = args.names or sorted(REGISTRY)
            results, failures = {}, {}
            for name in names:
                try:
                    results[name] = refresh(conn, get(name))
                except Exception as e:   # re-raised below, after the other studies
                    failures[name] = e
            if failures:
                raise RuntimeError(f"study refresh failed for {sorted(failures)}: "
                                   + "; ".join(f"{n}: {e}" for n, e in failures.items())
                                   + f" (refreshed: {sorted(results)})") from next(iter(failures.values()))
            return results
        case "status":
            return status(config, conn, args.name, by=args.by)
        case "export":
            return export(config, conn, args.name, output=args.output,
                          link_transcripts=args.link_transcripts)
    raise ValueError(f"unhandled study action {args.study_command}")
