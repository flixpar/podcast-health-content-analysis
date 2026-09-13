import argparse
import json
from pathlib import Path

import pytest

from analysis import topic_labeling as tl
from analysis.benchmark import contrast as contrast_mod
from analysis.benchmark import items as items_mod
from analysis.benchmark import matching, references, runner, scoring, stats, synthetic
from analysis.benchmark.taxonomy import label_axes, load_benchmark_taxonomy

ROOT = Path(__file__).resolve().parents[2]
TAXONOMY = load_benchmark_taxonomy(ROOT / "benchmark" / "taxonomy.json")
AXES = label_axes(TAXONOMY)

UNITS = [
    "Welcome back to the show everybody.",
    "Magnesium glycinate probably adds about forty minutes of deep sleep.",
    "A Stanford study found that in most people.",
    "I take the Vitalyx magnesium every night and it works.",
    "Anyway the game last night was wild.",
    "This episode is brought to you by Nordlite, use code POD for twenty percent off.",
]


def make_item(item_id="c1w0001", stratum="health_dense", split="dev", texts=UNITS):
    units = [
        {"unit_id": f"u{i + 1:06d}", "text": t, "start_seconds": None, "end_seconds": None,
         "timing_quality": "unavailable", "source_segment_index": 0}
        for i, t in enumerate(texts)
    ]
    return {
        "schema_version": tl.SCHEMA_VERSION, "window_id": f"episode_1_window_{item_id[-4:]}", "episode_id": 1,
        "window_index": 1, "podcast_id": None, "podcast_title": None, "episode_title": None,
        "published_date": None, "duration_seconds": None, "source_transcript": None,
        "source_transcript_sha256": None, "transcript_source": "asr", "transcript_model": None,
        "language": "en", "start_seconds": None, "end_seconds": None, "timing_quality": "unavailable",
        "word_count": sum(len(t.split()) for t in texts), "units": units,
        "item_id": item_id, "stratum": stratum, "split": split, "source": "corpus", "tags": [],
        "provenance": {"podcast_id": 1}, "features": {}, "added_in": "v1",
    }


def detection(start, end, labels, quote, relevance="substantive", role="asserted_or_endorsed", conf=0.9):
    return {"start_unit_id": start, "end_unit_id": end, "label_ids": labels, "relevance": relevance,
            "discourse_role": role, "confidence": conf, "summary": "s", "evidence_quote": quote}


def claim(start, end, text, quote, certainty="hedged", markers=("probably",), role="asserted_or_endorsed",
          ctype="treatment_or_prevention", relevance="substantive"):
    return {"start_unit_id": start, "end_unit_id": end, "topic_ids": ["topic:sleep"], "frame_ids": [],
            "evidence_signal_ids": [], "discourse_role": role, "claim_type": ctype, "claim_text": text,
            "expressed_certainty": certainty, "certainty_markers": list(markers), "evidence_quote": quote,
            "confidence": 0.8, "rationale": "r", "relevance": relevance}


def product(start, end, name, quote, ptype="supplement", role="recommended"):
    return {"start_unit_id": start, "end_unit_id": end, "product_name": name, "product_type": ptype,
            "mention_role": role, "evidence_quote": quote, "confidence": 0.9}


def result(window_id, detections=(), claims=(), products=()):
    return {"window_id": window_id, "detections": list(detections), "verification_candidates": list(claims),
            "product_mentions": list(products)}


def reference_result(item, variant=0):
    """Three slightly different but valid reference labelings."""
    d = [detection("u000002", "u000003", ["topic:sleep"], "deep sleep")]
    if variant != 2:
        d.append(detection("u000003", "u000003", ["cross_cutting:scientific_study_citation"], "Stanford study found"))
    if variant == 1:
        d.append(detection("u000006", "u000006", ["cross_cutting:commercialization"], "brought to you by", relevance="advertisement"))
    c = [claim("u000002", "u000002", "Magnesium glycinate probably adds about forty minutes of deep sleep.", "adds about forty minutes of deep sleep")]
    p = [product("u000004", "u000004", "Vitalyx" if variant != 2 else "Vitalyx magnesium", "Vitalyx magnesium")]
    return references.validate_result(result(item["window_id"], d, c, p), item, AXES)


def test_validate_result_keeps_claim_relevance_and_rejects_bad_values():
    item = make_item()
    normalized = reference_result(item)
    assert normalized["verification_candidates"][0]["relevance"] == "substantive"
    bad = result(item["window_id"], claims=[claim("u000002", "u000002", "x", "deep sleep", relevance="nope")])
    with pytest.raises(tl.TopicLabelingError):
        references.validate_result(bad, item, AXES)


def test_explode_makes_one_atom_per_label_and_locates_quotes():
    item = make_item()
    index = matching.WindowIndex(item)
    res = result(item["window_id"], [detection("u000002", "u000003", ["topic:sleep", "topic:functional_nutrition_supplements"], "deep sleep")])
    atoms = matching.explode(references.validate_result(res, item, AXES), index)
    assert [a.label for a in atoms] == ["topic:functional_nutrition_supplements", "topic:sleep"]
    assert all(a.quote_range is not None for a in atoms)
    assert index.text[atoms[0].quote_range[0]:atoms[0].quote_range[1]] == "deep sleep"


def test_aggregate_tiers_and_votes():
    item = make_item()
    refs = {a: {"result": reference_result(item, v)} for a, v in (("a", 0), ("b", 1), ("c", 2))}
    golds = references.gold_for_item(item, refs, {})
    by_key = {(g.kind, g.label): g for g in golds}
    sleep = by_key[("detection", "topic:sleep")]
    assert sleep.tier == "required" and sleep.support == pytest.approx(1.0)
    study = by_key[("detection", "cross_cutting:scientific_study_citation")]
    assert study.tier == "required" and len(study.annotators) == 2
    ad = by_key[("detection", "cross_cutting:commercialization")]
    assert ad.tier == "singleton"
    claims = [g for g in golds if g.kind == "claim"]
    assert len(claims) == 1 and claims[0].tier == "required"
    products = [g for g in golds if g.kind == "product"]
    assert len(products) == 1 and set(products[0].product_keys) == {"vitalyx", "vitalyxmagnesium"}
    assert products[0].vote_share("product_name", "Vitalyx") == pytest.approx(2 / 3)
    # Deterministic
    again = references.gold_for_item(item, refs, {})
    assert [references.gold_record(item, g) for g in golds] == [references.gold_record(item, g) for g in again]


def test_scoring_credits_required_ignores_singletons_and_penalises_extra_labels():
    item = make_item()
    refs = {a: {"result": reference_result(item, v)} for a, v in (("a", 0), ("b", 1), ("c", 2))}
    golds = references.gold_for_item(item, refs, {})
    pred = references.validate_result(result(
        item["window_id"],
        [detection("u000002", "u000003", ["topic:sleep", "topic:vaccines_immunization"], "deep sleep"),
         detection("u000006", "u000006", ["cross_cutting:commercialization"], "brought to you by", relevance="advertisement")],
        [claim("u000002", "u000002", "Magnesium glycinate probably adds forty minutes of deep sleep.", "adds about forty minutes of deep sleep")],
        [product("u000004", "u000004", "vitalyx", "Vitalyx magnesium")],
    ), item, AXES)
    row = scoring.score_item(item, pred, golds)
    topic = row["counts"]["detection:topic"]
    assert topic["tp"] == 1 and topic["fp"] == 1 and topic["fn"] == 0
    frame = row["counts"]["detection:frame"]
    assert frame.get("unscored", 0) == 1 and frame.get("fp", 0) == 0
    assert row["counts"]["detection:evidence"]["fn"] == 1
    assert row["counts"]["claim"]["tp"] == 1
    assert row["counts"]["product"]["tp"] == 1
    classes = {e["class"] for e in row["errors"] if e["type"] == "false_positive"}
    assert "same_axis_wrong_label" in classes
    summary = scoring.summarize([row])
    assert summary["groups"]["detection:topic"]["precision"] == 0.5
    assert summary["groups"]["detection:topic"]["recall_strict"] == 1.0
    certainty = summary["attributes"]["claim:expressed_certainty"]
    assert certainty["exact"] == 1.0


def test_aggregate_skips_items_with_one_annotator():
    item = make_item()
    refs = {item["item_id"]: {"a": {"result": reference_result(item, 0)}}}
    records, agreement = references.aggregate([item], refs, {}, {})
    assert records == [] and agreement["items_below_min_annotators"] == 1
    refs[item["item_id"]]["b"] = {"result": reference_result(item, 1)}
    records, agreement = references.aggregate([item], refs, {}, {})
    assert records and agreement["items_in_gold"] == 1


def test_span_rule_accepts_nested_extents_but_not_a_marginal_overlap():
    gold = matching.GoldAtom("g", "detection", (2, 9), (0, 11), "topic", "topic:sleep", "required", 1.0, ["a"], {}, [], [], [], [], [])
    inside = matching.Atom("detection", 3, 7, axis="topic", label="topic:sleep")
    clause = matching.Atom("detection", 4, 4, axis="topic", label="topic:sleep")
    wider = matching.Atom("detection", 0, 11, axis="topic", label="topic:sleep")
    edge = matching.Atom("detection", 8, 15, axis="topic", label="topic:sleep")
    other = matching.Atom("detection", 3, 7, axis="topic", label="topic:food_nutrition")
    assert matching.match_score(inside, gold) > 0
    assert matching.match_score(clause, gold) > 0  # same phenomenon, narrower extent
    assert matching.match_score(wider, gold) > 0
    assert matching.match_score(edge, gold) == 0  # only a quarter of it overlaps
    assert matching.match_score(other, gold) == 0
    assert matching.match_score(inside, gold) > matching.match_score(clause, gold)  # closer extent wins assignment


def test_stats_helpers():
    assert stats.weighted_kappa([(0, 0), (1, 1), (2, 2), (3, 3)], 4) == pytest.approx(1.0)
    assert stats.krippendorff_alpha([["a", "a"], ["b", "b"], ["a", "a"]]) == pytest.approx(1.0)
    alpha = stats.krippendorff_alpha([["a", "b"], ["b", "a"], ["a", "b"]])
    assert alpha is not None and alpha < 0
    assert stats.auroc([0.9, 0.8, 0.2, 0.1], [True, True, False, False]) == 1.0
    rows_a = [{"tp": 1, "fp": 1, "fn": 0}] * 20
    rows_b = [{"tp": 2, "fp": 0, "fn": 0}] * 20
    boot = stats.paired_bootstrap(rows_a, rows_b, stats.pooled_f1, iterations=200)
    assert boot["delta"] > 0 and boot["low"] > 0


def test_pairwise_agreement_is_symmetric_and_perfect_for_identical_labels():
    item = make_item()
    index = matching.WindowIndex(item)
    atoms = matching.explode(reference_result(item, 0), index)
    agreement = references.pairwise_f1(atoms, atoms)
    assert all(v["f1"] == 1.0 for v in agreement.values())


def test_contrast_pair_attribute_move_and_noop():
    base = make_item()
    twin_units = list(UNITS)
    twin_units[1] = "Magnesium glycinate adds about forty minutes of deep sleep."
    twin = make_item(item_id="t-c1w0001--remove_hedge", stratum="contrast", texts=twin_units)
    twin.update({"source": "contrast", "window_id": base["window_id"] + "_remove_hedge", "pair_id": "p", "base_item_id": base["item_id"],
                 "perturbation": "remove_hedge", "edited_unit_ids": ["u000002"], "target": {"unit_ids": ["u000002"]},
                 "expected_delta": {"kind": "claim", "field": "expressed_certainty", "from": ["hedged"], "to": ["unhedged"], "decoy": False, "noop": False, "collateral_allowed": []}})
    base_res = references.validate_result(result(base["window_id"], claims=[claim("u000002", "u000002", "x", "deep sleep")]), base, AXES)
    twin_res = references.validate_result(result(twin["window_id"], claims=[claim("u000002", "u000002", "x", "deep sleep", certainty="unhedged", markers=())]), twin, AXES)
    row = contrast_mod.evaluate_pair(base, twin, base_res, twin_res, None)
    assert row["passed"] is True and row["collateral_changed"] == 0
    noop = dict(twin, expected_delta={"kind": None, "unchanged": True, "decoy": False, "noop": True, "collateral_allowed": []}, perturbation="noop")
    row = contrast_mod.evaluate_pair(base, noop, base_res, base_res, None)
    assert row["passed"] is True


def test_synthetic_item_and_contrast_item_checks():
    entry = {"slug": "certainty-hedged", "sentences": [f"Sentence number {i} about sleep and magnesium and the body and rest tonight." for i in range(45)],
             "planted": {"claims": [{"sentence_start": 3, "sentence_end": 3, "claim_text": "x", "expressed_certainty": "hedged"}]}}
    item = synthetic.synthetic_item(entry)
    assert item["units"][0]["unit_id"] == "u000001" and item["planted"]["claims"][0]["start_unit_id"] == "u000004"
    with pytest.raises(items_mod.BenchmarkError):
        synthetic.synthetic_item({**entry, "sentences": ["too short"] * 8})
    base = make_item()
    edited = [{"unit_id": u["unit_id"], "text": u["text"]} for u in base["units"]]
    edited[1]["text"] = "Magnesium glycinate adds about forty minutes of deep sleep."
    twin = synthetic.contrast_item({"pair_id": "c1w0001--remove_hedge", "perturbation": "remove_hedge", "units": edited, "target": {}}, base)
    assert twin["edited_unit_ids"] == ["u000002"] and twin["expected_delta"]["to"] == ["unhedged"]
    bad = [dict(u, text=u["text"] + " x") for u in edited]
    with pytest.raises(items_mod.BenchmarkError):
        synthetic.contrast_item({"pair_id": "c1w0001--remove_hedge", "perturbation": "remove_hedge", "units": bad}, base)


def test_runner_records_attempts_and_repeats(tmp_path, monkeypatch):
    items = [make_item("c1w0001"), make_item("c2w0001")]
    items[1]["window_id"] = "episode_2_window_0001"
    calls = {"n": 0}

    def fake_classify(self, window, taxonomy, model, settings, instructions=None, on_attempt=None, validation="strict"):
        calls["n"] += 1
        if calls["n"] == 1:
            on_attempt({"attempt": 0, "ok": False, "window_id": window["window_id"], "seconds": 0.1, "kind": "non_verbatim_quote", "message": "m", "usage": {"input_tokens": 10, "output_tokens": 5}})
            raise tl.TopicLabelingError("bad quote", kind="non_verbatim_quote")
        on_attempt({"attempt": 0, "ok": True, "window_id": window["window_id"], "seconds": 0.1, "response_id": f"r{calls['n']}", "usage": {"input_tokens": 10, "output_tokens": 5}})
        return result(window["window_id"]), {"response_id": f"r{calls['n']}", "usage": {"input_tokens": 10, "output_tokens": 5}, "response_model": model, "effective_sampling": {}}

    monkeypatch.setattr(tl.ResponsesClient, "classify", fake_classify)
    monkeypatch.setattr(tl.ResponsesClient, "served_models", lambda self: {"http://x/v1": "stub-model"})
    args = runner.label_args(["--api-base", "http://x/v1", "--model", "stub-model", "--concurrency", "1", "--reasoning-effort", "none"], config=None)
    manifest = runner.run_benchmark(items, TAXONOMY, args, "stub", repeats=2, runs_dir=tmp_path, log=None)
    assert manifest["repeats"] == 2 and manifest["items"] == 2
    assert "batch_size" not in manifest
    # One request per window: the rejected window fails alone, and its
    # neighbour in the same repeat is labeled regardless.
    assert calls["n"] == 4
    assert [s["windows_labeled"] for s in manifest["repeat_summaries"]] == [1, 2]
    assert manifest["repeat_summaries"][0]["unresolved_windows_by_kind"] == {"non_verbatim_quote": 1}
    assert not any("isolat" in key for s in manifest["repeat_summaries"] for key in s)
    loaded = runner.load_run(tmp_path / "stub")
    assert len(loaded["repeats"]) == 2 and set(loaded["repeats"][1]) == {"episode_1_window_0001", "episode_2_window_0001"}
    assert len(loaded["repeats"][0]) == 1
    usage = runner.usage_summary(loaded["attempts"], {"input_per_mtok": 1.0, "output_per_mtok": 2.0})
    assert usage["rejected_by_kind"] == {"non_verbatim_quote": 1}
    assert usage["windows_accepted"] == 3 and usage["cost_usd"] > 0
    assert manifest["validator_sha256"] and manifest["items_hash"]


def test_usage_summary_still_reads_attempts_from_batched_runs():
    """An attempts log written before one-window requests lists its windows."""
    attempts = [
        {"attempt": 0, "ok": True, "windows": ["a", "b", "c", "d"], "seconds": 1.0, "usage": {"input_tokens": 10, "output_tokens": 5}},
        {"attempt": 0, "ok": False, "windows": ["e", "f"], "seconds": 1.0, "kind": "omitted_windows"},
        {"attempt": 0, "ok": True, "window_id": "g", "seconds": 1.0, "usage": {"input_tokens": 10, "output_tokens": 5}},
    ]
    usage = runner.usage_summary(attempts, None)
    assert usage["windows_accepted"] == 5
    assert usage["rejected_by_kind"] == {"omitted_windows": 1}


def test_run_fingerprint_ignores_item_set_and_bookkeeping():
    from analysis.benchmark import runner

    base = {"schema_version": 1, "prompt_version": "p", "rubric_sha256": "r", "taxonomy_sha256": "t", "model": "m", "api": "responses", "reasoning_effort": "low"}
    grown = {**base, "items_hash": "other", "name": "x", "notes": "resumed", "repeat": 1, "items": 200}
    changed = {**base, "reasoning_effort": "high"}
    assert runner.fingerprint_from_manifest(base) == runner.fingerprint_from_manifest(grown)
    assert runner.fingerprint_from_manifest(base) != runner.fingerprint_from_manifest(changed)
    # A manifest from a batched run keeps its batch_size input, so it still
    # recomputes to its own fingerprint and never to a one-window run's.
    batched = {**base, "batch_size": 4}
    assert runner.fingerprint_from_manifest(batched) != runner.fingerprint_from_manifest(base)


def test_adjudication_survives_an_added_annotator_and_required_is_a_count():
    item = make_item()
    refs = {item["item_id"]: {"a": {"result": reference_result(item, 0)}, "b": {"result": reference_result(item, 1)}, "c": {"result": reference_result(item, 2)}}}
    records, _ = references.aggregate([item], refs, {}, {})
    singles = [r for r in records if r["tier"] == "singleton"]
    assert singles, "fixture should leave at least one singleton"
    target = singles[0]
    overlay = {(item["item_id"], target["members"][0]): {"tier": "rejected", "member": target["members"][0]}}
    records2, _ = references.aggregate([item], refs, {}, overlay)
    assert [r["tier"] for r in records2 if r["members"] == target["members"]] == ["rejected"]
    # A fourth annotator that repeats annotator a's labels re-clusters everything; the verdict
    # still lands on the same atom, and atoms a and d share become required by count (2 of 4).
    refs[item["item_id"]]["d"] = {"result": reference_result(item, 0)}
    records3, _ = references.aggregate([item], refs, {}, overlay)
    hit = [r for r in records3 if target["members"][0] in r["members"]]
    assert len(hit) == 1
    assert hit[0]["tier"] in ("rejected", "required")
    assert all(r["tier"] == "required" for r in records3 if len(r["annotators"]) >= 2)
    assert all(r["tier"] != "required" for r in records3 if len(r["annotators"]) < 2)


def test_adjacent_credit_counts_a_reference_confusion_pair_once():
    item = make_item()
    last = min(2, len(item["units"]) - 1)
    gold = [matching.GoldAtom("g", "detection", (0, last), (0, last), "topic", "topic:food_nutrition", "required", 1.0, ["a", "b"], {}, [], [], [], [], [])]
    result = {
        "window_id": item["window_id"],
        "detections": [
            {"start_unit_id": item["units"][0]["unit_id"], "end_unit_id": item["units"][last]["unit_id"], "axis": "topic", "label_ids": ["topic:functional_nutrition_supplements"], "relevance": "substantive", "discourse_role": "asserted_or_endorsed", "confidence": 0.8, "summary": "s", "evidence_quote": item["units"][0]["text"]},
        ],
        "verification_candidates": [],
        "product_mentions": [],
    }
    strict = scoring.score_item(item, result, gold)
    assert strict["counts"]["detection:topic"]["fp"] == 1 and strict["counts"]["detection:topic"]["fn"] == 1
    adjacency = {tuple(sorted(("topic:food_nutrition", "topic:functional_nutrition_supplements")))}
    loose = scoring.score_item(item, result, gold, adjacency=adjacency)
    assert loose["counts"]["detection:topic"]["adjacent"] == 1
    pooled = scoring._pool([loose], "detection:topic")
    assert pooled["f1_strict"] == 0.0 and pooled["f1_adjacent"] == 1.0



def test_runner_threads_validation_and_totals_what_lenient_changed(tmp_path, monkeypatch):
    items = [make_item("c1w0001"), make_item("c2w0001")]
    items[1]["window_id"] = "episode_2_window_0001"
    modes = []

    def fake_classify(self, window, taxonomy, model, settings, instructions=None, on_attempt=None, validation="strict"):
        modes.append(validation)
        changes = (
            {"repaired": {"span_widened_for_quote": 1}, "dropped": {"non_verbatim_quote": 2}}
            if validation == "lenient"
            else {"repaired": {}, "dropped": {}}
        )
        summary = {"mode": validation, **changes}
        on_attempt({"attempt": 0, "ok": True, "window_id": window["window_id"], "seconds": 0.1, "usage": None, "validation": summary})
        return result(window["window_id"]), {"response_id": "r", "usage": None, "response_model": model, "effective_sampling": {}, "validation": summary}

    monkeypatch.setattr(tl.ResponsesClient, "classify", fake_classify)
    monkeypatch.setattr(tl.ResponsesClient, "served_models", lambda self: {"http://x/v1": "stub-model"})
    flags = ["--api-base", "http://x/v1", "--model", "stub-model", "--concurrency", "1", "--reasoning-effort", "none"]
    strict = runner.run_benchmark(items, TAXONOMY, runner.label_args(flags, config=None), "strict", repeats=1, runs_dir=tmp_path)
    lenient = runner.run_benchmark(
        items, TAXONOMY, runner.label_args([*flags, "--validation", "lenient"], config=None), "lenient", repeats=2, runs_dir=tmp_path
    )
    assert modes == ["strict"] * 2 + ["lenient"] * 4
    assert (strict["validation"], lenient["validation"]) == ("strict", "lenient")
    assert strict["run_fingerprint"] != lenient["run_fingerprint"]
    # The totals are bookkeeping: a finished manifest recomputes to its own fingerprint.
    assert runner.fingerprint_from_manifest(lenient) == lenient["run_fingerprint"]

    assert strict["validation_changes"] == {"repaired": {}, "dropped": {}}
    assert lenient["repeat_summaries"][0]["validation_changes"] == {
        "repaired": {"span_widened_for_quote": 2},
        "dropped": {"non_verbatim_quote": 4},
    }
    assert lenient["validation_changes"] == {
        "repaired": {"span_widened_for_quote": 4},
        "dropped": {"non_verbatim_quote": 8},
    }
    usage = runner.usage_summary(runner.load_run(tmp_path / "lenient")["attempts"], None)
    # Accepted with drops is still accepted.
    assert usage["accepted"] == 4 and usage["first_attempt_validity"] == 1.0
    assert usage["annotations_repaired"] == {"span_widened_for_quote": 4}
    assert usage["annotations_dropped"] == {"non_verbatim_quote": 8}
