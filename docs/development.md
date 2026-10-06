# Developing the pipeline

Start with [the repository overview](../README.md) and the guide for the
workflow you are changing. This is a research pipeline with an existing
catalog and corpus: preserve recorded provenance, dataset boundaries and
resume behavior when extending it.

## Run the offline suite

From the repository root on Linux x86-64 with Python 3.13 and `uv`:

```bash
UV_PROJECT_ENVIRONMENT=local/test-venv uv sync --locked --only-group test
local/test-venv/bin/python -m pytest
# Narrow checks when working on one subsystem:
local/test-venv/bin/python -m pytest analysis/tests
local/test-venv/bin/python -m pytest downloader/tests
uv lock --check
```

Install `ffmpeg`/`ffprobe` and `rg` to exercise audio and corpus-search checks.
The Qwen backend tests use fake HTTP/model clients and generated audio; they
are part of the offline suite. GPU inference, production endpoint behavior,
full-corpus performance and fresh reference annotation require separate
validation and should be reported separately.

The `test` group omits production dependencies. Using `--only-group test` on
an existing production environment would remove its unselected packages;
keep the explicit `local/test-venv` environment for testing. For production,
use the setup commands in the [downloader guide](../downloader/README.md).

GitHub Actions runs the same locked test group on pull requests and pushes to
`main`. Tests are discovered only in `analysis/tests` and `downloader/tests`;
archived worktrees, data volumes and generated task bundles are excluded.

## Keep contracts and artifacts consistent

- Put maintained source, small authored fixtures and portable examples in Git.
  Put generated runs, reports and scratch files under ignored `local/` or the
  configured data volume. Preserve superseded research documents in `local/`
  rather than discarding their original versions.
- Keep downloader defaults in `podcast_pipeline/config.py` synchronized with
  `config.example.json`. Resolve stored database paths through
  `podcast_pipeline.paths`; back up a legacy catalog before path migration.
- Select a study revision when a population must be reproducible. Use its
  exported membership and provenance rather than a fresh live query.
- Edit a taxonomy, its codebook and matching rubric together. Preparation and
  benchmark compilation must select the same version. V3 uses v8; older gold
  requires new annotation under changed rules.
- Treat prompt/schema fingerprints and checkpoint behavior as compatibility
  contracts. Output-affecting changes require a new run. TypeSafe remains
  flat-only and should fail before inference on hierarchical input.
- Keep inference and serving settings explicit in a configuration. Credentials
  belong in environment variables or an ignored `.env`, following `.env.example`.
- The usage limiter deliberately retains its existing shared database at
  `analysis/output/usage-limits.sqlite` unless explicitly configured otherwise.
  Preserve that ledger when moving data; resetting it also resets recorded
  budgets. Existing label runs can be reopened with their explicit output path.

Run tests appropriate to the change, inspect `git diff --check`, and document
any corpus, GPU or endpoint validation still needed. When dependencies change,
update `pyproject.toml` and `uv.lock` together; the lockfile is the reproducible
version selection for both production and tests.
