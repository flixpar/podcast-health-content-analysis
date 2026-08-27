# Preliminary vaccine-content tagging

`vaccine_tagging.py` provides a fast exploratory pipeline for the recovered Qwen
ASR corpus in `/tmp/fparker9/podcasts`. It deliberately separates lexical
retrieval from model filtering so that the candidate queue is inspectable and
the expensive step can be resumed.

```bash
python analysis/vaccine_tagging.py scan
python analysis/vaccine_tagging.py tag --api-base http://127.0.0.1:8222/v1
python analysis/vaccine_tagging.py report
python analysis/render_vaccine_html.py
python analysis/append_research_agenda.py
```

Default outputs are under `analysis/output/vaccine-preliminary/`:

- `candidates.jsonl`: high-recall lexical matches with episode metadata,
  original 10-minute segment boundaries, estimated clip times, and ASR text.
- `clip_tags.jsonl`: candidates plus Qwen relevance, content-type, stance,
  topic, claim, review-flag, and notability tags.
- `episodes.csv`: one row per episode with relevant content.
- `review_queue.csv`: clip-level, score-sorted table for rapid human review.
- `podcast_summary.csv`: corpus denominators and retrieved/tagged counts by show.
- `preliminary_findings.md`: kickoff-ready toplines and clips to review.
- `analysis_document.html`: self-contained internal methods and results memo.
- `analysis_document_with_research_agenda.html`: preserved memo plus an integrated
  research agenda based on the pilot findings and `project-pitch.md`.
- JSON summaries and a retryable `tagging_failures.jsonl` audit trail.

This is research triage, not a validated measurement or fact-check. In
particular, `potential_misinformation` is a model-generated review flag that
must be checked against the audio, full context, and reliable evidence.
