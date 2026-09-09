from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mf_lab.analysis.synthetic_features import extract_synthetic_feature_bank


@dataclass
class Sample:
    path: Path
    label: int
    generator: str
    split: str
    transform: str


def load_manifest(path: str | Path) -> list[Sample]:
    path = Path(path)
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            p = Path(row["path"])
            if not p.is_absolute():
                p = (path.parent / p).resolve()
            label_raw = str(row["label"]).strip().lower()
            label = 1 if label_raw in {"1", "synthetic", "fake", "ai", "deepfake"} else 0
            rows.append(Sample(
                p,
                label,
                row.get("generator", "unknown") or "unknown",
                row.get("split", "test") or "test",
                row.get("transform", "original") or "original",
            ))
    if not rows:
        raise ValueError("manifest contains no samples")
    return rows


def _matrix(samples: list[Sample]):
    names = None
    X = []
    for s in samples:
        bank = extract_synthetic_feature_bank(s.path)
        feats = bank["features"]
        if names is None:
            names = sorted(feats)
        X.append([float(feats[n]) for n in names])
    return np.asarray(X, dtype=float), np.asarray([s.label for s in samples], dtype=int), names or []


def _metrics(y, pred, score=None) -> dict:
    from sklearn.metrics import (
        accuracy_score,
        average_precision_score,
        balanced_accuracy_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    result = {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall_sensitivity": float(recall_score(y, pred, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else None,
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else None,
        "f1": float(f1_score(y, pred, zero_division=0)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }
    if score is not None and len(np.unique(y)) == 2:
        result["roc_auc"] = float(roc_auc_score(y, score))
        result["pr_auc"] = float(average_precision_score(y, score))
    else:
        result["roc_auc"] = None
        result["pr_auc"] = None
    return result


def _candidate_estimators(seed: int = 42):
    from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC
    return {
        "logistic": Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=3000, class_weight="balanced", random_state=seed)),
        ]),
        "svm_rbf": Pipeline([
            ("scale", StandardScaler()),
            ("clf", SVC(C=2.0, gamma="scale", class_weight="balanced", probability=True, random_state=seed)),
        ]),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=300,
            class_weight="balanced",
            random_state=seed,
            n_jobs=-1,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(random_state=seed),
    }


def run_benchmark(
    manifest: str | Path,
    out: str | Path,
    model_out: str | Path | None = None,
    cross_generator: bool = False,
    seed: int = 42,
) -> dict:
    """Run a scientific synthetic-image benchmark separate from regression CI.

    Required manifest columns: path,label. Recommended: generator,split,transform.
    Splits must be predeclared to avoid leakage. The benchmark never modifies GT.
    """
    from sklearn.base import clone
    import joblib

    samples = load_manifest(manifest)
    train = [s for s in samples if s.split.lower() == "train"]
    test = [s for s in samples if s.split.lower() == "test"]
    if not train or not test:
        raise ValueError("manifest must contain explicit train and test splits")
    if len({s.label for s in train}) < 2 or len({s.label for s in test}) < 2:
        raise ValueError("train and test must each contain real and synthetic samples")

    Xtr, ytr, names = _matrix(train)
    Xte, yte, names_te = _matrix(test)
    if names != names_te:
        raise RuntimeError("feature schema mismatch")

    models = {}
    fitted = {}
    for name, est in _candidate_estimators(seed).items():
        est.fit(Xtr, ytr)
        pred = est.predict(Xte)
        score = est.predict_proba(Xte)[:, 1] if hasattr(est, "predict_proba") else None
        models[name] = _metrics(yte, pred, score)
        fitted[name] = est

    best_name = max(
        models,
        key=lambda n: (models[n]["balanced_accuracy"], models[n].get("roc_auc") or -1),
    )
    best = fitted[best_name]

    by_generator = {}
    for gen in sorted({s.generator for s in test}):
        idx = [i for i, s in enumerate(test) if s.generator == gen]
        if not idx:
            continue
        yy = yte[idx]
        pp = best.predict(Xte[idx])
        ss = best.predict_proba(Xte[idx])[:, 1] if hasattr(best, "predict_proba") else None
        if len(np.unique(yy)) == 2:
            by_generator[gen] = _metrics(yy, pp, ss)
        else:
            by_generator[gen] = {
                "n": len(idx),
                "class_distribution": {
                    str(int(v)): int(np.sum(yy == v)) for v in np.unique(yy)
                },
                "note": "single-class subgroup; confusion-derived rates omitted",
            }

    by_transform = {}
    for tr in sorted({s.transform for s in test}):
        idx = [i for i, s in enumerate(test) if s.transform == tr]
        yy = yte[idx]
        pp = best.predict(Xte[idx])
        ss = best.predict_proba(Xte[idx])[:, 1] if hasattr(best, "predict_proba") else None
        by_transform[tr] = (
            _metrics(yy, pp, ss)
            if len(np.unique(yy)) == 2
            else {"n": len(idx), "note": "single-class subgroup"}
        )

    logo = {}
    if cross_generator:
        synthetic_generators = sorted({
            s.generator
            for s in samples
            if s.label == 1 and s.generator not in {"real", "camera", "unknown"}
        })
        for held in synthetic_generators:
            tr_samples = [
                s for s in samples
                if s.generator != held and s.split.lower() != "test_holdout"
            ]
            te_samples = [
                s for s in samples
                if s.generator == held or (s.label == 0 and s.split.lower() == "test")
            ]
            if len({s.label for s in tr_samples}) < 2 or len({s.label for s in te_samples}) < 2:
                continue
            xa, ya, nn = _matrix(tr_samples)
            xb, yb, nn2 = _matrix(te_samples)
            if nn != nn2:
                continue
            est = clone(_candidate_estimators(seed)[best_name])
            est.fit(xa, ya)
            pred = est.predict(xb)
            score = est.predict_proba(xb)[:, 1] if hasattr(est, "predict_proba") else None
            logo[held] = _metrics(yb, pred, score)

    result = {
        "protocol": "MFLAB-SCI-SYNTH-0.1",
        "manifest": str(manifest),
        "sample_count": len(samples),
        "train_count": len(train),
        "test_count": len(test),
        "feature_count": len(names),
        "feature_names": names,
        "models": models,
        "selected_model": best_name,
        "selected_model_metrics": models[best_name],
        "by_generator": by_generator,
        "by_transform": by_transform,
        "leave_one_generator_out": logo,
        "interpretation": "Scientific benchmark metrics estimate performance only for the declared dataset/splits. They do not establish universal forensic validity.",
    }
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    if model_out:
        bundle = {
            "model_name": f"mflab_handcrafted_{best_name}",
            "estimator": best,
            "feature_names": names,
            "calibrated": hasattr(best, "predict_proba"),
            "validated": False,
            "validation": {
                "protocol": result["protocol"],
                "report": str(out),
                "metrics": models[best_name],
            },
        }
        model_out = Path(model_out)
        model_out.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(bundle, model_out)
    return result
