"""A learned screen: TF-IDF + logistic regression distilled from LLM labels.

Trains on corpus windows a full labeler annotated (the reference run), with the
target "the labeler produced any annotation" (or a stricter class), and writes
out-of-fold scores for those windows (5 folds grouped by episode, so a window
is never scored by a model that saw its own episode) plus scores for every
other window from a model fit on all of them.

    python exp/learned_screen.py --reference-run exp/corpus/v8-ref --name tfidf-lr \
        --windows <corpus windows.jsonl.zst>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "exp"))
from analysis import topic_labeling as tl  # noqa: E402
from screens import CLASSES, run_atoms, write_scores  # noqa: E402

TARGETS = {
    "any": lambda atoms: bool(atoms),
    "substantive": lambda atoms: any(CLASSES["topic (substantive)"](a) or a["kind"] == "claim" or CLASSES["topic (ad)"](a) for a in atoms),
}


def text(window) -> str:
    return " ".join(u["text"] for u in window["units"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-run", required=True)
    parser.add_argument("--windows", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--target", default="any", choices=list(TARGETS))
    parser.add_argument("--C", type=float, default=4.0)
    args = parser.parse_args()

    ref = run_atoms(Path(args.reference_run))
    corpus = list(tl.iter_jsonl(Path(args.windows)))
    bench = [json.loads(line) for line in open(REPO / "benchmark/v2/items.jsonl")]
    train = [w for w in corpus if w["window_id"] in ref]
    rest = [w for w in corpus if w["window_id"] not in ref] + bench
    y = np.array([TARGETS[args.target](ref[w["window_id"]]) for w in train], dtype=int)
    groups = np.array([w["episode_id"] for w in train])
    print(f"train {len(train)} windows, positive {y.mean():.3f}")

    def fit(windows, labels):
        vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=300_000, sublinear_tf=True, strip_accents="unicode")
        x = vec.fit_transform([text(w) for w in windows])
        model = LogisticRegression(C=args.C, max_iter=2000, class_weight="balanced")
        model.fit(x, labels)
        return vec, model

    scores: dict[str, float] = {}
    for fold, (tr, te) in enumerate(GroupKFold(n_splits=5).split(train, y, groups)):
        vec, model = fit([train[i] for i in tr], y[tr])
        p = model.predict_proba(vec.transform([text(train[i]) for i in te]))[:, 1]
        for i, s in zip(te, p):
            scores[train[i]["window_id"]] = float(s)
    vec, model = fit(train, y)
    p = model.predict_proba(vec.transform([text(w) for w in rest]))[:, 1]
    for w, s in zip(rest, p):
        scores[w["window_id"]] = float(s)
    write_scores(args.name, scores)
    terms = np.array(vec.get_feature_names_out())
    order = np.argsort(model.coef_[0])
    print("top positive:", ", ".join(terms[order[-40:]][::-1]))
    print("top negative:", ", ".join(terms[order[:20]]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
