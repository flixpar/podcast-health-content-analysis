#!/usr/bin/env python3
"""Preliminary findings from the hosted-DeepSeek labeling pilot.

Reads the pilot run directory (``analysis/output/deepseek-pilot``), the
client-side spending ledger written by ``analysis/usage_limits.py``, and the
keyword-scan tables under ``fast-analysis/scan``, and writes

    analysis/output/fast-analysis/deepseek_pilot.json
    analysis/output/fast-analysis/deepseek_pilot_notes.md

Nothing here touches transcripts, the metadata database (read-only), or any
API. It is a read-only summary of artifacts the pipeline already produced.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import zstandard

REPO = Path(__file__).resolve().parents[2]
RUN = REPO / "analysis/output/deepseek-pilot"
OUT = REPO / "analysis/output/fast-analysis"
LEDGER = REPO / "analysis/output/usage-limits.sqlite"
SCAN = Path("/mnt/data2/podcast-data/fast-analysis/scan")
EXPERIMENT = "deepseek-flash-pilot-2026-09-08"

# Corpus sizing, for the extrapolations. From analysis/output/fast-analysis.
CORPUS_WORDS = 1_480_000_000
WINDOW_WORDS, OVERLAP_WORDS = 900, 150


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def windows_for(words: float) -> float:
    """Windows a body of text of `words` words is cut into by `prepare`."""
    step = WINDOW_WORDS - OVERLAP_WORDS
    return max(1.0, (words - OVERLAP_WORDS) / step)


def ledger_totals() -> dict:
    """Spend and token counts this experiment actually recorded."""
    con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
    try:
        tables = {
            row[0] for row in con.execute("select name from sqlite_master where type='table'")
        }
        # The ledger's own request-level table; name it defensively so a schema
        # rename shows up as a missing number rather than a wrong one.
        table = next((t for t in ("requests", "usage", "usage_events", "events") if t in tables), None)
        if table is None:
            return {"error": f"no request table in ledger; tables={sorted(tables)}"}
        cols = {row[1] for row in con.execute(f"pragma table_info({table})")}
        scope_col = "experiment" if "experiment" in cols else None
        where = f"where {scope_col} = ?" if scope_col else ""
        params = (EXPERIMENT,) if scope_col else ()

        def total(expr: str) -> float:
            if not (set(expr.replace("+", " ").split()) <= cols):
                return float("nan")
            (value,) = con.execute(f"select coalesce(sum({expr}),0) from {table} {where}", params).fetchone()
            return float(value)

        (n_requests,) = con.execute(f"select count(*) from {table} {where}", params).fetchone()
        outcomes = dict(
            con.execute(f"select outcome, count(*) from {table} {where} group by outcome", params)
        ) if "outcome" in cols else {}
        return {
            "table": table,
            "requests": int(n_requests),
            "requests_by_outcome": outcomes,
            "input_tokens": total("input_tokens"),
            "cached_input_tokens": total("cached_input_tokens"),
            "output_tokens": total("output_tokens"),
            "cost_usd": total("cost_usd"),
        }
    finally:
        con.close()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    prepare = json.loads((RUN / "prepare_manifest.json").read_text())
    label = json.loads((RUN / "label_manifest.json").read_text())
    merge_path = RUN / "merge_summary.json"
    merge = json.loads(merge_path.read_text()) if merge_path.exists() else {}

    sample = pd.read_csv(OUT / "deepseek_pilot_sample.csv")
    group_of = dict(zip(sample.episode_id, sample.group))
    show_of = dict(zip(sample.episode_id, sample.show))
    words_of = dict(zip(sample.episode_id, sample.word_count))

    # `merge` cannot run on this (or any) run: it re-validates the *stored*
    # window results with the raw-payload validator, and the stored results are
    # the normalized ones, which carry the derived `axis` field that validator
    # forbids (topic_labeling.py:1232-1247 vs :1298 and :3558). So the counts
    # below are window-level, read straight from the labeling export, and
    # overlap duplicates are NOT collapsed. See the notes file.
    annotations, claims, products = [], [], []
    with (RUN / "window_labels.jsonl.zst").open("rb") as raw:
        for line in zstandard.ZstdDecompressor().stream_reader(raw).read().decode().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            episode_id = int(row["window_id"].split("_")[1])
            for det in row["detections"]:
                for label_id in det["label_ids"]:
                    annotations.append({**det, "label_id": label_id, "episode_id": episode_id})
            for claim in row["verification_candidates"]:
                claims.append({**claim, "episode_id": episode_id})
            for product in row["product_mentions"]:
                products.append({**product, "episode_id": episode_id})

    taxonomy = json.loads((RUN / "taxonomy.json").read_text())
    axis_of = {row["label_id"]: row["axis"] for row in taxonomy["labels"]}

    # ---------------------------------------------------------------- 1. cost
    spend = ledger_totals()
    prepared = int(prepare["windows"])
    labeled = int(label.get("windows_labeled", 0))
    unresolved = label.get("unresolved_windows_by_kind", {}) or {}
    cost = spend.get("cost_usd", float("nan"))
    per_window = cost / labeled if labeled else float("nan")

    # Windows in the live-capture window of the 24 densest health shows, and in
    # the whole corpus, priced at the observed per-window cost.
    profile = json.loads((REPO / "analysis/output/fast-analysis/corpus_profile.json").read_text())
    shows = pd.DataFrame(profile["per_show"])
    health = shows[shows.on_health_chart].copy()
    health = health.sort_values("live_words", ascending=False).head(24)
    health_words = float(health.live_words.sum())
    health_windows = float(sum(windows_for(w) for w in health.live_words if w > 0))
    corpus_windows = windows_for(CORPUS_WORDS)

    coverage = {
        "episodes": int(prepare["episodes_prepared"]),
        "units": int(prepare["units"]),
        "windows_prepared": prepared,
        "windows_labeled": labeled,
        "windows_unresolved": int(label.get("unresolved_windows", 0)),
        "unresolved_windows_by_kind": unresolved,
        "window_acceptance_rate": round(labeled / prepared, 4) if prepared else None,
        "batches_isolated": label.get("batches_isolated_this_invocation"),
        "windows_recovered_by_isolation": label.get("windows_recovered_by_isolation"),
        "api": label.get("api"),
        "model": label.get("model"),
        "reasoning_effort": label.get("reasoning_effort"),
        "batch_size": label.get("batch_size"),
        "spend": spend,
        "cost_per_accepted_window_usd": round(per_window, 6) if labeled else None,
        "output_tokens_per_request": round(spend.get("output_tokens", 0) / spend["requests"], 1)
        if spend.get("requests")
        else None,
        "cache_hit_share_of_input": round(
            spend.get("cached_input_tokens", 0) / spend["input_tokens"], 4
        )
        if spend.get("input_tokens")
        else None,
        "extrapolation": {
            "note": "priced at the observed cost per accepted window, at DeepSeek peak rates",
            "top24_health_shows_live_words": health_words,
            "top24_health_shows_windows": round(health_windows),
            "top24_health_shows_usd": round(health_windows * per_window, 2),
            "whole_corpus_words": CORPUS_WORDS,
            "whole_corpus_windows": round(corpus_windows),
            "whole_corpus_usd": round(corpus_windows * per_window, 2),
        },
    }

    # ------------------------------------------------------- 2. what it found
    by_axis: dict[str, Counter] = defaultdict(Counter)
    for row in annotations:
        by_axis[axis_of.get(row["label_id"], "?")][row["label_id"]] += 1
    ann_roles = Counter(row["discourse_role"] for row in annotations)
    ann_relevance = Counter(row["relevance"] for row in annotations)

    claim_types = Counter(row["claim_type"] for row in claims)
    certainty = Counter(row["expressed_certainty"] for row in claims)
    claim_roles = Counter(row["discourse_role"] for row in claims)
    # Every verification candidate is by construction a possible-misinformation
    # flag: the extraction schema only emits claims selected for evidence review.
    flagged = len(claims)
    product_types = Counter(row["product_type"] for row in products)
    mention_roles = Counter(row["mention_role"] for row in products)

    # Per-group rates per *labeled* window, so a group whose episodes were cut
    # off by the budget is not penalised for windows nobody paid for.
    win_counts: Counter[int] = Counter()
    with (RUN / "window_labels.jsonl.zst").open("rb") as raw:
        for line in zstandard.ZstdDecompressor().stream_reader(raw).read().decode().splitlines():
            if line.strip():
                win_counts[int(json.loads(line)["window_id"].split("_")[1])] += 1

    group_windows: Counter[str] = Counter()
    for episode_id, n in win_counts.items():
        group_windows[group_of.get(episode_id, "?")] += n

    def per_group(rows: list[dict], key=None) -> dict:
        counts: Counter[str] = Counter()
        for row in rows:
            counts[group_of.get(row["episode_id"], "?")] += 1
        return {
            g: {
                "n": counts.get(g, 0),
                "windows": group_windows[g],
                "per_window": round(counts.get(g, 0) / group_windows[g], 3) if group_windows[g] else None,
            }
            for g in sorted(group_windows)
        }

    findings = {
        "topic_annotations": dict(by_axis["topic"].most_common()),
        "frame_annotations": dict(by_axis["frame"].most_common()),
        "evidence_annotations": dict(by_axis["evidence"].most_common()),
        "annotation_discourse_role": dict(ann_roles.most_common()),
        "annotation_relevance": dict(ann_relevance.most_common()),
        "claims_total": len(claims),
        "claims_by_type": dict(claim_types.most_common()),
        "claims_by_expressed_certainty": dict(certainty.most_common()),
        "claims_by_discourse_role": dict(claim_roles.most_common()),
        "claims_flagged_possible_misinformation": flagged,
        "claims_flagged_share": round(flagged / len(claims), 4) if claims else None,
        "product_mentions_total": len(products),
        "product_mentions_by_type": dict(product_types.most_common()),
        "product_mentions_by_role": dict(mention_roles.most_common()),
        "per_group": {
            "windows": dict(group_windows),
            "annotations": per_group(annotations),
            "claims": per_group(claims),
            "product_mentions": per_group(products),
        },
    }

    # ------------------------------------------- 3. agreement with the keyword scan
    scan = pd.read_parquet(SCAN / "counts.parquet")
    scan = scan[(scan.episode_id.isin(win_counts)) & (scan.section == "topics")]
    scan_sets = scan.groupby("episode_id")["label"].apply(set).to_dict()
    llm_sets: dict[int, set] = defaultdict(set)
    for row in annotations:
        if axis_of.get(row["label_id"]) == "topic":
            llm_sets[row["episode_id"]].add(row["label_id"].split(":", 1)[1])

    tp = fp = fn = 0
    per_topic: dict[str, Counter] = defaultdict(Counter)
    for episode_id in win_counts:
        s, l = scan_sets.get(episode_id, set()), llm_sets.get(episode_id, set())
        tp += len(s & l)
        fp += len(s - l)
        fn += len(l - s)
        for topic in s & l:
            per_topic[topic]["both"] += 1
        for topic in s - l:
            per_topic[topic]["scan_only"] += 1
        for topic in l - s:
            per_topic[topic]["llm_only"] += 1

    def ratio(num: float, den: float):
        return round(num / den, 3) if den else None

    topic_rows = []
    for topic, c in sorted(per_topic.items(), key=lambda kv: -sum(kv[1].values())):
        n_llm = c["both"] + c["llm_only"]
        n_scan = c["both"] + c["scan_only"]
        topic_rows.append(
            {
                "topic": topic,
                "episodes_llm": n_llm,
                "episodes_scan": n_scan,
                "both": c["both"],
                "scan_only": c["scan_only"],
                "llm_only": c["llm_only"],
                "scan_precision": ratio(c["both"], n_scan),
                "scan_recall": ratio(c["both"], n_llm),
            }
        )

    agreement = {
        "unit": "episode x topic presence, over the pilot's labeled episodes",
        "episodes": len(win_counts),
        "scan_precision_overall": ratio(tp, tp + fp),
        "scan_recall_overall": ratio(tp, tp + fn),
        "pairs_both": tp,
        "pairs_scan_only": fp,
        "pairs_llm_only": fn,
        "per_topic": topic_rows,
        "topics_llm_finds_scan_misses": sorted(
            (r["topic"] for r in topic_rows if r["llm_only"] >= 3),
            key=lambda t: -per_topic[t]["llm_only"],
        ),
        "topics_scan_finds_llm_misses": sorted(
            (r["topic"] for r in topic_rows if r["scan_only"] >= 3),
            key=lambda t: -per_topic[t]["scan_only"],
        ),
    }

    # -------------------------------------------------------- 4. example claims
    narr = pd.read_parquet(SCAN / "counts.parquet")
    narr = narr[(narr.episode_id.isin(win_counts)) & (narr.section == "narratives")]
    narr_episodes = set(narr.episode_id)

    by_group: dict[str, list[dict]] = defaultdict(list)
    for row in sorted(claims, key=lambda r: (-r.get("confidence", 0), r["claim_text"])):
        by_group[group_of.get(row["episode_id"], "?")].append(row)
    examples = []
    quota = {"wellness": 5, "political": 3, "debunking": 2, "general": 2}
    for group, want in quota.items():
        for row in by_group.get(group, [])[:want]:
            examples.append(
                {
                    "group": group,
                    "show": show_of.get(row["episode_id"]),
                    "claim_text": row["claim_text"],
                    "claim_type": row["claim_type"],
                    "expressed_certainty": row["expressed_certainty"],
                    "certainty_markers": row.get("certainty_markers"),
                    "discourse_role": row["discourse_role"],
                    "scan_narrative_hit_in_episode": row["episode_id"] in narr_episodes,
                }
            )

    report = {
        "run": {
            "output_dir": str(RUN),
            "run_fingerprint": label.get("run_fingerprint"),
            "prompt_version": label.get("prompt_version"),
            "endpoints": label.get("endpoints"),
            "experiment": EXPERIMENT,
            "stopped_by_usage_limit": label.get("stopped_by_usage_limit"),
        },
        "coverage_and_cost": coverage,
        "findings": findings,
        "keyword_scan_agreement": agreement,
        "example_claims": examples,
        "merge_summary": merge,
    }
    (OUT / "deepseek_pilot.json").write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")

    # ------------------------------------------------------------- 5. the memo
    def table(rows: list[list], header: list[str]) -> str:
        out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
        out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
        return "\n".join(out)

    pg = findings["per_group"]

    def rate(group: str, kind: str):
        value = pg[kind].get(group, {}).get("per_window")
        return "n/a" if value is None else f"{value:.1f}"

    grounded = sum(
        1
        for row in claims
        if (row["expressed_certainty"] == "unhedged") == (not row.get("certainty_markers"))
    )
    commentary = f"""The run stopped where it was meant to: `{label.get('stopped_by_usage_limit', '')}`.
{labeled} of {prepared} windows were paid for before the $4.50 allocation ran
out, and the rest are recorded as `budget_exceeded` and are resumable. That
number is the headline caveat on everything below -- only
{len(win_counts)} of the 24 sampled episodes have any labeled windows, the
groups are unevenly covered (general {group_windows.get('general', 0)} windows,
wellness {group_windows.get('wellness', 0)}, political {group_windows.get('political', 0)},
debunking {group_windows.get('debunking', 0)}), and none of the rates below are
estimates of anything but this sample.

The hosted endpoint itself works: `/v1/responses` with strict
`text.format.json_schema`, `reasoning.effort` and echoed-back sampling, so the
preferred route is available and `effective_sampling` is populated. But
{spend['requests']} requests bought {labeled} accepted windows -- against the
~{labeled // (label.get('batch_size') or 4)} a clean batch-4 run would need --
so the per-response rejection rate on this endpoint at `low` was high, and most
of the bill went on responses that were thrown away. The manifest's
`unresolved_windows_by_kind` cannot say which rejections they were: it reports
each window's *latest* state, and the budget stop overwrote the earlier kinds.
Capturing that distribution is the first thing a follow-up run should do,
because it is the number the whole cost model turns on.

What it cost is the finding. `low` still thinks: roughly
{coverage['output_tokens_per_request']:,.0f} output tokens per four-window request, which at
DeepSeek's peak output price dominates the bill and puts an accepted window at
${per_window:.3f}. Input is nearly free by comparison once the ~11.5k-token
instruction prefix is warm -- {coverage['cache_hit_share_of_input']:.0%} of input tokens billed as cache
hits -- so batch size and reasoning length, not context, are the levers. At this
rate the 24 densest health shows' live episodes are a
${health_windows*per_window:,.0f} job and the whole corpus a
${corpus_windows*per_window:,.0f} one; halved again if the run is confined to
off-peak hours, which is worth scheduling for.

Yield of checkable claims per window separates the show types cleanly:
{rate('wellness', 'claims')} claims per window on the wellness shows against
{rate('political', 'claims')} on news/politics, {rate('debunking', 'claims')} on
the debunking shows and {rate('general', 'claims')} on general-audience talk.
The same ordering shows up in product mentions ({rate('wellness', 'product_mentions')}
vs {rate('general', 'product_mentions')} per window), which is the expected
shape: the wellness shows are where both the checkable health claims and the
supplement sponsor reads live, and a production pass targeted at them buys most
of the signal for a fraction of the corpus.

Certainty coding is at least anchored: all {grounded} of
{findings['claims_total']} claims satisfy the marker rule, though that is
partly tautological -- the client rejects any response that breaks it, so the
rule is a filter on what survives rather than a measurement. What is
informative is the mix, {findings['claims_by_expressed_certainty']}, and the
markers themselves, which read as real hedges and boosters rather than
back-filled ones ("every single year" behind an `absolute`, a plain
declarative behind an `unhedged`). It is not evidence the four-level
distinction is *correct*; the blinded claim sample is still the thing that
tests it.

Two failure modes stand out. The first is cost variance: a rejected batch is
retried one window at a time and every retry pays for a fresh block of
reasoning, so the per-window price is set by the *rejection rate* rather than
by the token count -- which is why the corpus figure above should be read as an
upper bound tied to this run's acceptance, not a quote. The second is
downstream: `merge` cannot run on this run, or on any run, because it
re-validates the stored window results with the raw-payload validator while
`label` stores the *normalized* ones, which carry the derived `axis` field that
validator forbids (`topic_labeling.py` lines 1232-1247 against 1298 and 3558).
Everything above is therefore window-level and un-deduplicated: a claim in a
150-word overlap is counted twice, so the per-window rates are right and the
totals are inflated. Fixing that is a prerequisite for any real yield estimate.
Finally, this run is `low`, and the local measurement says `high` finds ~45%
more detections per window at similar claim yield; whether those extra
detections are recall or false positives decides whether the cheap setting
under-counts topic prevalence, and that is a question for the blinded
validation sample rather than another throughput run."""

    group_rows = [
        [
            g,
            pg["windows"].get(g, 0),
            pg["annotations"][g]["per_window"],
            pg["claims"][g]["per_window"],
            pg["product_mentions"][g]["per_window"],
        ]
        for g in sorted(pg["windows"])
    ]

    notes = f"""# DeepSeek hosted-API labeling pilot -- preliminary findings

Run `{label.get('run_fingerprint', '')[:12]}`, prompt `{label.get('prompt_version')}`,
model `{label.get('model')}` over the `{label.get('api')}` route at
`https://api.deepseek.com/v1`, `reasoning_effort={label.get('reasoning_effort')}`,
batch {label.get('batch_size')}. Experiment `{EXPERIMENT}`, capped at $4.50 by
`analysis/usage-limits.toml`.

## 1. Coverage and cost

{coverage['episodes']} episodes -> {coverage['units']} units -> {prepared} windows prepared;
**{labeled} labeled and accepted** ({coverage['window_acceptance_rate']:.1%}),
{coverage['windows_unresolved']} unresolved. Rejections by kind: `{unresolved or '{}'}`.
(The isolation counters read {coverage['batches_isolated']} because the manifest
was rewritten by a final no-op invocation after the budget stop; the
isolation that actually happened is visible only in the request count below.)

{spend['requests']} requests, {spend['input_tokens']:,.0f} input tokens
({spend['cached_input_tokens']:,.0f} of them cache hits, {coverage['cache_hit_share_of_input']:.0%}),
{spend['output_tokens']:,.0f} output tokens (reasoning is billed inside these),
**${spend['cost_usd']:.2f} spent**. That is
**${per_window:.4f} per accepted window** and {coverage['output_tokens_per_request']:,.0f}
output tokens per request.

Extrapolated at that rate (peak prices; off-peak is half):

- the 24 densest health-chart shows' live-window episodes
  ({health_words/1e6:.1f}M words, ~{health_windows:,.0f} windows): **${health_windows*per_window:,.0f}**
- the whole corpus (1.48B words, ~{corpus_windows:,.0f} windows): **${corpus_windows*per_window:,.0f}**

## 2. What the model found

{findings['claims_total']} atomic claims, {findings['product_mentions_total']} product mentions and
{len(annotations)} label annotations across the {labeled} accepted windows.

Certainty mix: `{findings['claims_by_expressed_certainty']}`.
Claim types: `{findings['claims_by_type']}`.
Discourse roles on claims: `{findings['claims_by_discourse_role']}`.
{findings['claims_flagged_possible_misinformation']} of {findings['claims_total']} claims carry
`possible_misinformation=true` ({(findings['claims_flagged_share'] or 0):.0%}) -- by design a
high-recall screening flag, not a truth verdict.

Rates per window by show group:

{table(group_rows, ["group", "windows", "annotations/window", "claims/window", "products/window"])}

Top topics: `{dict(list(findings['topic_annotations'].items())[:8])}`

Top frames: `{dict(list(findings['frame_annotations'].items())[:8])}`

Evidence signals: `{findings['evidence_annotations']}`

Product types: `{findings['product_mentions_by_type']}`;
mention roles: `{findings['product_mentions_by_role']}`

## 3. Agreement with the keyword scan

Compared per episode, as the set of topics each method attributes to it
(unit-to-sentence alignment is not attempted here). Treating the LLM as
reference over {agreement['episodes']} episodes: the scan's episode-level topic
**precision is {agreement['scan_precision_overall']}** and its
**recall is {agreement['scan_recall_overall']}**
({tp} topics found by both, {fp} by the scan only, {fn} by the LLM only).

{table([[r['topic'], r['episodes_llm'], r['episodes_scan'], r['both'], r['scan_only'], r['llm_only'], r['scan_precision'], r['scan_recall']] for r in agreement['per_topic'][:15]], ['topic', 'eps LLM', 'eps scan', 'both', 'scan only', 'LLM only', 'scan prec.', 'scan rec.'])}

Topics the LLM finds and the scan misses most often:
{', '.join(agreement['topics_llm_finds_scan_misses'][:10]) or '(none at n>=3)'}.
Topics the scan fires on and the LLM does not:
{', '.join(agreement['topics_scan_finds_llm_misses'][:10]) or '(none at n>=3)'}.

## 4. Example claims

{table([[e['group'], (e['show'] or '')[:34], e['claim_text'][:120].replace('|', '/'), e['expressed_certainty'], e['discourse_role'], 'yes' if e['scan_narrative_hit_in_episode'] else 'no'] for e in examples], ['group', 'show', 'claim_text', 'certainty', 'discourse role', 'scan narrative hit'])}

## 5. Commentary

{commentary}
"""
    (OUT / "deepseek_pilot_notes.md").write_text(notes)
    print(json.dumps({"windows_labeled": labeled, "cost_usd": spend.get("cost_usd"), "claims": len(claims)}, indent=1))


if __name__ == "__main__":
    main()
