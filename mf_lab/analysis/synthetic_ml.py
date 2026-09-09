from __future__ import annotations

import os
from pathlib import Path


def _default_model_path() -> Path | None:
    raw = os.environ.get("MFLAB_SYNTHETIC_MODEL")
    return Path(raw) if raw else None


def score_synthetic_ml(feature_bank: dict, model_path: str | Path | None = None) -> dict:
    """Score a handcrafted feature vector with an explicitly configured model.

    No bundled classifier is silently treated as validated. The model bundle must
    include feature_names, estimator, calibration metadata and validation metadata.
    """
    path = Path(model_path) if model_path else _default_model_path()
    if path is None:
        return {
            "status": "not_configured",
            "validated": False,
            "warning": "Set MFLAB_SYNTHETIC_MODEL to a validated joblib bundle to enable ML scoring.",
        }
    if not path.is_file():
        return {"status": "error", "validated": False, "error": f"model_not_found: {path}"}
    try:
        import joblib
        import numpy as np
    except Exception as exc:
        return {"status": "error", "validated": False, "error": f"model_runtime_unavailable: {exc!r}"}
    try:
        bundle = joblib.load(path)
        names = list(bundle["feature_names"])
        values = feature_bank.get("features", {})
        x = np.asarray([[float(values[n]) for n in names]], dtype=float)
        estimator = bundle["estimator"]
        if hasattr(estimator, "predict_proba"):
            probability = float(estimator.predict_proba(x)[0, 1])
            raw_score = probability
        elif hasattr(estimator, "decision_function"):
            raw_score = float(estimator.decision_function(x)[0])
            probability = None
        else:
            raw_score = float(estimator.predict(x)[0])
            probability = None
        pred = int(estimator.predict(x)[0])
        validation = bundle.get("validation", {}) or {}
        calibrated = bool(bundle.get("calibrated", False))
        validated = bool(bundle.get("validated", False))
        return {
            "status": "success",
            "model_name": bundle.get("model_name", path.stem),
            "model_path": str(path),
            "predicted_label": "synthetic" if pred == 1 else "real",
            "score": raw_score,
            "calibrated_probability_synthetic": probability if calibrated else None,
            "calibrated": calibrated,
            "validated": validated,
            "validation": validation,
            "warning": "A model score is evidence only within its documented validation domain; domain shift and unseen generators remain material risks.",
        }
    except Exception as exc:
        return {"status": "error", "validated": False, "error": repr(exc)}
