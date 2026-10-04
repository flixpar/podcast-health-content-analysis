# Turning corpus-review proposals into label-set patches: shared brief

Corpus-review agents searched ~145k podcast transcripts and proposed edits to the
v8 label set (`/home/felix/projects/podcasts/podcast-misinfo/taxonomy/health-v8.md`;
rules in `taxonomy/codebook-v8.md`). You are the editor for the reports your task
names. Read the codebook and the affected parts of the label set first, then each
assigned report in full.

Do NOT edit any repository file. Your output is a patch file plus a decision log.

## How to judge each proposal

Accept, modify or reject every proposed CHANGE / ADD / REMOVE / MERGE in your
reports. The goal is a label set a careful coder can apply consistently to real
podcast talk, granular enough for health-misinformation research, and not inflated.

- **Evidence first.** Accept changes backed by corpus evidence (counts, read
  samples). Reject speculative ones.
- **ADD** only when the subject recurs (roughly 30+ episodes across 3+ podcasts,
  or clearly important for misinformation research), is distinct from existing
  labels, and is worth counting separately. Otherwise widen an existing
  definition instead.
- **REMOVE** only labels that are essentially absent AND unimportant for
  misinformation research; prefer keeping a rare but important narrative.
- **Definitions** stay short (1 to 3 sentences), stance-neutral for topics, with
  boundary sentences naming the neighbouring label (backticked, real IDs, in the
  short `parent.leaf` form inside topic tables, full `axis:id` elsewhere, as the
  file already does). Narrative definitions start with one bold core proposition
  (`**...**`) and keep one direction.
- **Examples** should be phrases people actually say (from the reports' samples),
  `;`-separated, no `|` characters anywhere in a cell.
- **Scope rules belong in the codebook, not the label set.** Proposals that are
  really health-content boundary rules (what counts as health talk at all: idioms,
  recreational substance scenery, crime narration, COVID as a time marker, drug-ad
  boilerplate, political issue lists) are codebook material: do not encode them
  as labels; just record them in your decision log under "codebook".
- Keep IDs stable. Rename an ID only if the current one is actively misleading.
  Never reuse a removed ID for a different meaning.
- If two of your reports touch the same label, merge them into one op.
- Use exact current IDs. Before writing a CHANGE, look up the current row in
  health-v8.md and start from it; keep what is right and change what the evidence
  supports.

## Output 1: patch file (JSONL, one op per line)

```
{"op": "change", "id": "topic:vaccines.hep_b", "row": "| hep_b | Hepatitis B vaccine | ... | ... |"}
{"op": "add", "under": "topic:infectious", "row": "| new_slug | Name | Definition. | ex1; ex2 |"}
{"op": "add", "under": "vaccines_narratives", "row": "| new_slug | Name | **Core.** Elaboration. | ex1; ex2 | home_parent |"}
{"op": "add", "under": "frame", "row": "| new_slug | Name | Definition. | ex1; ex2 |"}   (also "evidence", "population")
{"op": "remove", "id": "narrative:some_id"}
{"op": "parent", "id": "topic:covid", "definition": "New parent definition paragraph.", "name": "Optional new parent name"}
```

- `change` replaces the whole row; the row's first cell must be the label's own slug.
- Topic subtopic rows have 4 cells; narrative rows have 5 (last = home parent topic
  slug without `topic:`, which must exist); frame/evidence/population rows have 4.
- A narrative `add` goes under its family id (`vaccines_narratives`,
  `covid_narratives`, `cancer_narratives`, `food_narratives`, `pharma_narratives`,
  `wellness_narratives`, `hormone_narratives`, `system_narratives`,
  `other_narratives`).
- Validate before finishing: run
  `python3 /tmp/claude-1000/-home-felix-projects-podcasts-podcast-misinfo/4b5c1f41-b91b-4f1c-8d8b-15dde473d3b5/scratchpad/corpus-review/apply_patches.py /home/felix/projects/podcasts/podcast-misinfo/taxonomy/health-v8.md /tmp/claude-1000/-home-felix-projects-podcasts-podcast-misinfo/4b5c1f41-b91b-4f1c-8d8b-15dde473d3b5/scratchpad/corpus-review/check-<your group>.md <your patch file>`
  then, from `/home/felix/projects/podcasts/podcast-misinfo`,
  `.venv/bin/python -c "from analysis import topic_labeling as tl; tl.compile_taxonomy('<that check .md>')"`.
  Both must succeed. Also check that every backticked reference in your rows names
  a label that exists after your patch (other groups' new labels do not exist yet:
  do not reference them).

## Output 2: decision log (markdown)

For every proposal in your reports: one line `ACCEPT | MODIFY | REJECT  <id>  reason`.
Then a section `## Codebook` listing the codebook/prompt suggestions from your
reports that you judge sound (with the report and evidence), and a section
`## Cross-slice notes` for anything that touches labels outside your reports'
slices (do not patch those).

Final message: the two output paths and counts (changes / adds / removes /
parent edits, and rejections). Nothing else.
