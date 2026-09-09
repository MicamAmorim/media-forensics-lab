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
        reader = csv.DictReader(f)
        if not reader.fieldnames or not {"path", "label"}.issubset(set(reader.fieldnames)):
            raise ValueError("manifest must contain path and label columns")
        for row in reader:
            p = Path(row["path"])
            if not p.is_absolute():
                p = (path.parent / p).resolve()
            label_raw = str(row["label"]).strip().lower()
            if label_raw not in {"0", "1", "real", "synthetic", "fake", "ai", "deepfake"}:
                raise ValueError(f"unsupported label: {row['label']}")
            label = 1 if label_raw in {"1", "synthetic", "fake", "ai", "deepfake"} else 0
            split = (row.get("split") or "test").strip().lower()
            if split == "val":
                split = "validation"
            if split not in {"train", "validation", "test", "test_holdout"}:
                raise ValueError(f"unsupported split: {split}")
            rows.append(Sample(
                p,
                label,
                row.get("generator", "unknown") or "unknown",
                split,
                row.get("transform", "original") or "original",
            ))
    if not rows:
        raise ValueError("manifest contains no samples")
    missing = [str(s.path) for s in rows if not s.path.is_file()]
    if missing:
        raise FileNotFoundError(f"manifest contains missing files; first={missing[0]}")
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
        brier_score_loss,
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
        result["brier_score"] = float(brier_score_loss(y, score))
    else:
        result["roc_auc"] = None
        result["pr_auc"] = None
        result["brier_score"] = None
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
        "extra_trees": ExtraTreesClassifier(n_estimators=300, class_weight="balanced", random_state=seed, n_jobs=-1),
        "hist_gradient_boosting": HistGradientBoostingClassifier(random_state=seed),
    }


def _selection_scores(X, y, estimators: dict, seed: int, validation=None) -> dict[str, float]:
    from sklearn.base import clone
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    scores = {}
    if validation is not None:
        Xv, yv = validation
        for name, est in estimators.items():
            candidate = clone(est).fit(X, y)
            scores[name] = float(balanced_accuracy_score(yv, candidate.predict(Xv)))
        return scores

    counts = np.bincount(y, minlength=2)
    folds = int(min(5, counts.min()))
    if folds < 2:
        raise ValueError("training split needs at least two samples in each class for model selection")
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    for name, est in estimators.items():
        scores[name] = float(np.mean(cross_val_score(est, X, y, cv=cv, scoring="balanced_accuracy")))
    return scores


def _fit_selected(estimator, X, y):
    """Fit selected estimator and calibrate when class counts permit."""
    from sklearn.base import clone
    from sklearn.calibration import CalibratedClassifierCV

    counts = np.bincount(y, minlength=2)
    folds = int(min(5, counts.min()))
    if folds >= 3:
        calibrated = CalibratedClassifierCV(clone(estimator), method="sigmoid", cv=folds)
        calibrated.fit(X, y)
        return calibrated, True
    fitted = clone(estimator).fit(X, y)
    return fitted, False


def run_benchmark(
    manifest: str | Path,
    out: str | Path,
    model_out: str | Path | None = None,
    cross_generator: bool = False,
    seed: int = 42,
) -> dict:
    """Run scientific synthetic-image validation separate from regression CI.

    Model selection never uses the final test set: an explicit validation split is
    preferred; otherwise stratified cross-validation is performed on training data.
    """
    from sklearn.base import clone
    import joblib

    samples = load_manifest(manifest)
    train = [s for s in samples if s.split == "train"]
    validation = [s for s in samples if s.split == "validation"]
    test = [s for s in samples if s.split == "test"]
    if not train or not test:
        raise ValueError("manifest must contain explicit train and test splits")
    if len({s.label for s in train}) < 2 or len({s.label for s in test}) < 2:
        raise ValueError("train and test must each contain real and synthetic samples")

    Xtr, ytr, names = _matrix(train)
    Xte, yte, names_te = _matrix(test)
    if names != names_te:
        raise RuntimeError("feature schema mismatch")

    validation_data = None
    if validation:
        Xv, yv, names_v = _matrix(validation)
        if names_v != names or len(np.unique(yv)) < 2:
            raise ValueError("validation split must share feature schema and contain both classes")
        validation_data = (Xv, yv)

    estimators = _candidate_estimators(seed)
    selection_scores = _selection_scores(Xtr, ytr, estimators, seed, validation=validation_data)
    best_name = max(selection_scores, key=selection_scores.get)

    fit_samples = train + validation
    Xfit, yfit, fit_names = _matrix(fit_samples)
    if fit_names != names:
        raise RuntimeError("feature schema mismatch after train+validation merge")
    best, calibrated = _fit_selected(estimators[best_name], Xfit, yfit)

    pred = best.predict(Xte)
    score = best.predict_proba(Xte)[:, 1] if hasattr(best, "predict_proba") else None
    final_metrics = _metrics(yte, pred, score)

    comparison = {}
    for name, est in estimators.items():
        fitted = clone(est).fit(Xfit, yfit)
        pp = fitted.predict(Xte)
        ss = fitted.predict_proba(Xte)[:, 1] if hasattr(fitted, "predict_proba") else None
        comparison[name] = _metrics(yte, pp, ss)

    by_generator = {}
    for gen in sorted({s.generator for s in test}):
        idx = [i for i, s in enumerate(test) if s.generator == gen]
        yy = yte[idx]
        pp = best.predict(Xte[idx])
        ss = best.predict_proba(Xte[idx])[:, 1] if hasattr(best, "predict_proba") else None
        by_generator[gen] = (
            _metrics(yy, pp, ss)
            if len(np.unique(yy)) == 2
            else {
                "n": len(idx),
                "class_distribution": {str(int(v)): int(np.sum(yy == v)) for v in np.unique(yy)},
                "note": "single-class subgroup; confusion-derived rates omitted",
            }
        )

    by_transform = {}
    for tr in sorted({s.transform for s in test}):
        idx = [i for i, s in enumerate(test) if s.transform == tr]
        yy = yte[idx]
        pp = best.predict(Xte[idx])
        ss = best.predict_proba(Xte[idx])[:, 1] if hasattr(best, "predict_proba") else None
        by_transform[tr] = _metrics(yy, pp, ss) if len(np.unique(yy)) == 2 else {"n": len(idx), "note": "single-class subgroup"}

    logo = {}
    if cross_generator:
        synthetic_generators = sorted({s.generator for s in samples if s.label == 1 and s.generator not in {"real", "camera", "unknown"}})
        for held in synthetic_generators:
            tr_samples = [s for s in samples if s.generator != held and s.split in {"train", "validation"}]
            te_samples = [s for s in samples if s.generator == held and s.split in {"validation", "test", "test_holdout"}]
            real_test = [s for s in samples if s.label == 0 and s.split == "test"]
            te_samples = te_samples + real_test
            if len({s.label for s in tr_samples}) < 2 or len({s.label for s in te_samples}) < 2:
                continue
            xa, ya, nn = _matrix(tr_samples)
            xb, yb, nn2 = _matrix(te_samples)
            if nn != nn2:
                continue
            est = clone(estimators[best_name]).fit(xa, ya)
            p = est.predict(xb)
            s = est.predict_proba(xb)[:, 1] if hasattr(est, "predict_proba") else None
            logo[held] = _metrics(yb, p, s)

    result = {
        "protocol": "MFLAB-SCI-SYNTH-0.2",
        "manifest": str(manifest),
        "sample_count": len(samples),
        "train_count": len(train),
        "validation_count": len(validation),
        "test_count": len(test),
        "feature_count": len(names),
        "feature_names": names,
        "model_selection_source": "validation" if validation else "stratified_cross_validation_on_train",
        "selection_balanced_accuracy": selection_scores,
        "selected_model": best_name,
        "selected_model_calibrated": calibrated,
        "selected_model_metrics": final_metrics,
        "comparison_on_final_test": comparison,
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
            "calibrated": calibrated,
            "validated": False,
            "validation": {"protocol": result["protocol"], "report": str(out), "metrics": final_metrics},
        }
        model_out = Path(model_out)
        model_out.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(bundle, model_out)
    return result
