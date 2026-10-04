# Corpus review behind the v8 label set and codebook

On 2026-10-04 the v8 scheme was checked against the transcript corpus
(~145.6k episodes, ~700 podcasts) with keyword search
(`analysis/corpus_text/cq.py`) and reading of real passages.

1. **Review** (`reports/`, brief in `review-brief.md`): 15 Opus agents, one per
   slice of the label set (11 topic slices, 2 narrative slices, frames/evidence/
   populations with the claim, ad and product mechanics) plus an open-ended
   coverage audit of 160 blind-sampled health passages. Each checked whether
   labels are findable, whether definitions and examples fit real talk, and what
   is missing, with counts and quoted passages.
2. **Patches** (`decisions/`, `patches/`, brief in `patch-brief.md`): editor
   agents accepted, modified or rejected every proposal and wrote label-set
   patches; `apply_patches.py` applied them by label ID, with the seven
   cross-slice overlaps merged by hand (`patches/resolved.jsonl`).
3. **Codebook** (`codebook-changes.md`): one editor folded the reports'
   codebook findings into `taxonomy/codebook-v8.md`, chiefly health-content
   boundary tests for the highest-volume false positives the corpus showed.

Counts in the reports are keyword hits (segments / episodes / podcasts), read
against samples; they are evidence of presence and volume, not prevalence
estimates.
