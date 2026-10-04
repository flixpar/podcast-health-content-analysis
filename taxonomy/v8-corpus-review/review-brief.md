# Corpus review of the v8 health labeling taxonomy: shared brief

## Context

We label podcast transcripts for health-information research (which specific
health subjects, contested narratives, framings, evidence types and populations
come up, and which checkable claims and products). The current scheme is v8:

- `/home/felix/projects/podcasts/podcast-misinfo/taxonomy/health-v8.md`: the label set
  (topic tree: domain → parent → subtopic; narratives; frames; evidence; populations).
- `/home/felix/projects/podcasts/podcast-misinfo/taxonomy/codebook-v8.md`: the rules.
- `/home/felix/projects/podcasts/podcast-misinfo/analysis/prompts/rubric-v8.md`: the labeler's procedure.

Read the codebook in full and the part of the label set you are assigned (and
skim the rest so you know where neighbouring subjects live). Do NOT edit any
of these files. Your job is evidence gathering and concrete proposals.

## The corpus and the search tool

About 145,000 transcribed episodes from several hundred podcasts (health and wellness shows, but also
comedy, true crime, news, business, sports, culture), flattened to one
transcript segment per line. Search it with:

```
python3 /mnt/internal/felix/podcast-corpus-text/cq.py count  'regex'            # hits: segments, episodes, podcasts + top podcasts
python3 /mnt/internal/felix/podcast-corpus-text/cq.py sample 'regex' -n 12 --ctx 1   # random hits with neighbouring segments
python3 /mnt/internal/felix/podcast-corpus-text/cq.py sample 'regex' --podcast 'huberman|attia'  # restrict to shows
python3 /mnt/internal/felix/podcast-corpus-text/cq.py ctx EPISODE SEGMENT -k 4       # read around a hit
python3 /mnt/internal/felix/podcast-corpus-text/cq.py cooc 'regex A' 'regex B'      # episodes with both
```

Patterns are case-insensitive Rust regexes (use `\b` for word boundaries,
`(a|b)` for alternatives; no lookarounds). Transcripts are speech recognition:
expect misspellings ("ozempic"/"ozempik", "glp one"), missing punctuation. A
query scans ~7 GB and takes a few seconds; prefer one alternation over many
separate queries. Keep `sample -n` modest and READ the samples: counts alone
mislead (e.g. "shot" is mostly not vaccines). Several other agents are
searching at the same time, so do not run more than one search at once.

## What to do for your slice

For each label (or each group of closely related labels) in your slice:

1. **Findability.** Build a keyword query from the label's name, definition and
   examples (plus the obvious real-world vocabulary). Count hits; sample and
   read real passages. Is the subject actually discussed in the corpus? Roughly
   how often (episodes, and how many different podcasts)? Note labels that are
   essentially absent (they may still be worth keeping, but say so).
2. **Definition fit.** Reading real passages, would a coder know which label to
   apply? Note real phrasing the definition or examples miss, frequent
   confusions with a neighbouring label, ambiguous boundary cases you actually
   saw (quote them briefly with ep/seg ids), and nuance the definition lacks.
3. **Examples.** Do the listed examples occur in the corpus and fit the label?
   Propose replacing artificial or misleading examples with the phrasing people
   actually use; add common real terms (including ASR variants worth knowing).
4. **Gaps / new subtopics.** While reading, look for recurring health subjects
   your parents' subtopics do not capture well (bare-parent territory). Search
   for them to estimate frequency. Propose a new subtopic only if it is
   (a) recurring across several podcasts (as a rough bar: 30+ episodes and 3+
   podcasts, or clearly important to health-misinformation research even if
   rarer), (b) distinct from existing labels, and (c) something researchers
   would want counted separately. Otherwise propose extending a definition.
5. **Merge or drop.** Flag labels that are near-duplicates, essentially absent
   and unimportant, or so broad they swallow neighbours.
6. **Codebook/prompt nuance.** Note real-language patterns the codebook rules do
   not handle well for your slice (e.g. how ads for these products actually
   sound, slang, how stances are signalled), with examples.

Be skeptical and quantitative. Prefer a few well-evidenced changes over many
speculative ones; do not inflate the taxonomy. Keep the labels stance-neutral
(topics name subjects, not positions).

## Output

Write ONE markdown file at the path your task gives you, with these sections:

```
# <slice name>: corpus review

## Summary
5-10 bullets: the most important findings and recommended changes.

## Label-by-label findings
For each label (or group): query used, counts (segments/episodes/podcasts),
verdict (fine / needs definition change / examples change / rare / merge / drop),
and 1-3 short real quotes with (ep, seg) where useful.

## Proposed edits
Each edit as one block, exactly one of:
- CHANGE `<full label id>`: new row in the file's own table format
  `| id | name | definition | examples |` (narratives: `| id | name | definition | examples | home topic |`),
  then one line "Why:" with the evidence.
- ADD `<full label id>` under `<parent or family>`: new row, then "Why:" with counts and 1-2 quotes.
- REMOVE or MERGE `<full label id>` [into `<id>`]: "Why:".
Keep table cells free of the `|` character. Narrative definitions start with
a bold core proposition (`**...**`). Use existing label IDs exactly; backticked
references must name real labels.

## Codebook and prompt notes
Concrete suggestions with the section of codebook-v8.md they belong in, and
evidence.
```

Your final message: the output path and a 3-line summary. Nothing else.
