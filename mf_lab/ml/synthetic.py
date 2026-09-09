from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

MODEL_SCHEMA = "MFLAB-SYNTH-ML-1.0"


def feature_schema_hash(feature_names: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(str(x) for x in feature_names).encode("utf-8")).hexdigest()


def _base_estimator(algorithm: str, random_state: int = 1337):
    name = algorithm.lower().strip()
    if name == "logistic":
        return Pipeline([("scale", StandardScaler()), ("model", LogisticRegression(max_iter=3000, class_weight="balanced", random_state=random_state))])
    if name == "extra_trees":
        return ExtraTreesClassifier(n_estimators=400, class_weight="balanced", random_state=random_state, n_jobs=-1, min_samples_leaf=2)
    if name == "svm_rbf":
        return Pipeline([("scale", StandardScaler()), ("model", SVC(kernel="rbf", C=2.0, gamma="scale", class_weight="balanced", probability=False, random_state=random_state))])
    if name == "xgboost":
        try:
            from xgboost import XGBClassifier
        except Exception as exc:
            raise RuntimeError("xgboost is optional; install `pip install -e .[ml-extra]`") from exc
        return XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, eval_metric="logloss", random_state=random_state, n_jobs=-1)
    raise ValueError("algorithm must be one of: svm_rbf, logistic, extra_trees, xgboost")


def train_classical_bundle(X, y, feature_names: list[str], *, algorithm="svm_rbf", calibration="sigmoid", calibration_cv=3, metadata=None, random_state=1337) -> dict:
    X = np.asarray(X, dtype=np.float64); y = np.asarray(y, dtype=np.int64).ravel()
    if X.ndim != 2 or len(X) != len(y) or X.shape[1] != len(feature_names):
        raise ValueError("X/y/feature_names dimensions are inconsistent")
    if len(set(y.tolist())) != 2:
        raise ValueError("binary labels 0=real and 1=synthetic are required")
    estimator = _base_estimator(algorithm, random_state)
    method = (calibration or "none").lower().strip()
    if method in {"sigmoid", "isotonic"}:
        counts = np.bincount(y, minlength=2); cv = int(min(counts.min(), calibration_cv))
        if cv < 2:
            raise ValueError("at least two samples per class are required for calibration")
        model = CalibratedClassifierCV(estimator=estimator, method=method, cv=cv); calibrated = True
    elif method == "none":
        model = estimator; calibrated = False
    else:
        raise ValueError("calibration must be sigmoid, isotonic or none")
    model.fit(X, y)
    meta = dict(metadata or {})
    meta.setdefault("task", "full_synthetic"); meta.setdefault("training_generators", []); meta.setdefault("training_families", [])
    meta.setdefault("scientifically_validated", False); meta.setdefault("validation_report", None)
    return {"schema": MODEL_SCHEMA, "model_kind": "handcrafted_classical", "algorithm": algorithm,
            "feature_schema_hash": feature_schema_hash(feature_names), "feature_names": list(feature_names),
            "calibrated": calibrated, "calibration": method, "metadata": meta, "model": model}


def save_bundle(bundle: dict, path: str | Path) -> Path:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True); joblib.dump(bundle, p); return p


def load_bundle(path: str | Path) -> dict:
    bundle = joblib.load(path)
    if not isinstance(bundle, dict) or bundle.get("schema") != MODEL_SCHEMA or "model" not in bundle or not bundle.get("feature_names"):
        raise ValueError(f"unsupported/invalid model bundle: {path}")
    return bundle


def predict_bundle(bundle: dict, feature_bank: dict, *, model_name: str | None = None) -> dict:
    names = list(feature_bank.get("feature_names") or []); expected = list(bundle.get("feature_names") or [])
    if names != expected:
        return {"status": "feature_schema_mismatch", "model": model_name,
                "expected_hash": bundle.get("feature_schema_hash"), "observed_hash": feature_schema_hash(names)}
    X = np.asarray(feature_bank.get("feature_values") or [], dtype=np.float64).reshape(1, -1)
    model = bundle["model"]; pred = int(model.predict(X)[0]); probability = raw_score = None
    if hasattr(model, "predict_proba"):
        proba = np.asarray(model.predict_proba(X), dtype=float)
        if proba.ndim == 2 and proba.shape[1] >= 2: probability = float(proba[0, 1])
    if hasattr(model, "decision_function"):
        try: raw_score = float(np.ravel(model.decision_function(X))[0])
        except Exception: pass
    meta = dict(bundle.get("metadata") or {})
    return {"status": "success", "schema": MODEL_SCHEMA, "model": model_name, "model_kind": bundle.get("model_kind"),
            "algorithm": bundle.get("algorithm"), "task": meta.get("task", "full_synthetic"),
            "label": "synthetic" if pred == 1 else "real", "score": raw_score if raw_score is not None else probability,
            "probability_synthetic": probability if bundle.get("calibrated") else None, "calibrated": bool(bundle.get("calibrated")),
            "scientifically_validated": bool(meta.get("scientifically_validated")), "validation": meta.get("validation_report"),
            "training_generators": meta.get("training_generators", []), "training_families": meta.get("training_families", []),
            "warning": "Model output is not an evidentiary conclusion; scientific validity requires an independent benchmark in the applicable domain."}


def _deep_configs(case: Path | None) -> list[Path]:
    paths=[]
    if case is not None and (case / "models" / "deep").is_dir():
        root=case/"models"/"deep"; paths += sorted([*root.glob("*.json"), *root.glob("*.yaml"), *root.glob("*.yml")])
    if os.environ.get("MFLAB_SYNTHETIC_DEEP_CONFIG"): paths.append(Path(os.environ["MFLAB_SYNTHETIC_DEEP_CONFIG"]))
    seen=set(); out=[]
    for p in paths:
        key=str(p.resolve()) if p.exists() else str(p)
        if key not in seen: seen.add(key); out.append(p)
    return out


def run_case_models(case_dir: str | Path | None, image_path: str | Path, feature_bank: dict) -> dict:
    case = Path(case_dir) if case_dir is not None else None
    paths=[]
    if case is not None and (case / "models" / "classical").is_dir(): paths += sorted((case/"models"/"classical").glob("*.joblib"))
    if os.environ.get("MFLAB_SYNTHETIC_MODEL"): paths.append(Path(os.environ["MFLAB_SYNTHETIC_MODEL"]))
    outputs=[]; seen=set()
    for p in paths:
        key=str(p.resolve()) if p.exists() else str(p)
        if key in seen: continue
        seen.add(key)
        try: outputs.append(predict_bundle(load_bundle(p), feature_bank, model_name=p.name))
        except Exception as exc: outputs.append({"status": "error", "model": p.name, "model_kind": "handcrafted_classical", "error": repr(exc)})
    for cfg in _deep_configs(case):
        try:
            from mf_lab.ml.deep import predict_deep_config
            outputs.append(predict_deep_config(image_path, cfg))
        except Exception as exc: outputs.append({"status": "error", "model": cfg.name, "model_kind": "deep", "error": repr(exc)})
    return {"status": "success" if outputs else "no_models_configured", "outputs": outputs, "model_count": len(outputs),
            "validated_models": sum(bool(x.get("scientifically_validated")) for x in outputs),
            "calibrated_models": sum(bool(x.get("calibrated")) for x in outputs),
            "warning": "Learned outputs remain separate from forensic conclusions and require independent validation metadata."}


def ensemble_outputs(native_outputs: dict, external_models: list[dict] | None = None) -> dict:
    candidates=[]
    for row in native_outputs.get("outputs", []) if isinstance(native_outputs, dict) else []:
        p=row.get("probability_synthetic")
        if row.get("scientifically_validated") is True and row.get("calibrated") is True and p is not None:
            candidates.append({"source": row.get("model"), "probability": float(p), "kind": row.get("model_kind")})
    for row in external_models or []:
        if row.get("validated") is True and row.get("calibrated") is True:
            p=row.get("probability_synthetic", row.get("score"))
            if p is not None and 0 <= float(p) <= 1: candidates.append({"source": row.get("model") or row.get("name"), "probability": float(p), "kind": "external"})
    if not candidates:
        return {"status": "insufficient_validated_calibrated_models", "model_count": 0, "ensemble_probability_synthetic": None,
                "warning": "No ensemble probability is produced without scientifically validated and calibrated model outputs."}
    vals=np.asarray([x["probability"] for x in candidates], dtype=float)
    return {"status": "screening_ensemble", "model_count": len(candidates), "members": candidates,
            "ensemble_probability_synthetic": float(vals.mean()), "model_disagreement_std": float(vals.std()),
            "warning": "The ensemble is a calibrated screening summary, not a forensic probability of falsity."}
