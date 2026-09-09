from __future__ import annotations

import os
from pathlib import Path


_BUILTIN_MODEL = "mflab_cifake_hgb_calibrated_v1.joblib"


def _builtin_model_path() -> Path:
    return Path(__file__).resolve().parents[1] / "models" / _BUILTIN_MODEL


def _default_model_path() -> Path | None:
    raw = os.environ.get("MFLAB_SYNTHETIC_MODEL")
    if raw:
        return Path(raw)
    builtin = _builtin_model_path()
    return builtin if builtin.is_file() else None


def _domain_scope(feature_bank: dict, bundle: dict) -> dict:
    validation = bundle.get("validation", {}) or {}
    declared = validation.get("domain") or validation.get("validation_domain") or bundle.get("validation_domain")
    expected_resolution = validation.get("input_resolution")
    if expected_resolution is None:
        dataset = validation.get("dataset")
        if isinstance(dataset, dict):
            expected_resolution = dataset.get("resolution")
    input_shape = feature_bank.get("input_shape") or []
    observed_resolution = None
    if len(input_shape) >= 2:
        observed_resolution = [int(input_shape[0]), int(input_shape[1])]

    geometry_match = None
    if expected_resolution is not None and observed_resolution is not None:
        if isinstance(expected_resolution, str) and "x" in expected_resolution.lower():
            parts = expected_resolution.lower().replace(" ", "").split("x")[:2]
            try:
                expected_resolution = [int(parts[0]), int(parts[1])]
            except Exception:
                expected_resolution = None
        if isinstance(expected_resolution, (list, tuple)) and len(expected_resolution) >= 2:
            geometry_match = observed_resolution == [int(expected_resolution[0]), int(expected_resolution[1])]

    confirmed = os.environ.get("MFLAB_SYNTHETIC_MODEL_DOMAIN_CONFIRMED", "0").strip().lower() in {"1", "true", "yes", "on"}
    if not confirmed:
        status = "unconfirmed"
    elif geometry_match is False:
        status = "confirmed_but_geometry_mismatch"
    else:
        status = "confirmed_match"
    return {
        "declared_validation_domain": declared,
        "expected_resolution": expected_resolution,
        "observed_resolution": observed_resolution,
        "geometry_match": geometry_match,
        "domain_confirmed_by_examiner": confirmed,
        "validation_scope_status": status,
    }


def score_synthetic_ml(feature_bank: dict, model_path: str | Path | None = None) -> dict:
    """Score a handcrafted feature vector with a configured or bundled model.

    The v0.9 bundled model is scientifically validated only inside its declared
    CIFAKE domain. The classifier may still produce a machine label for arbitrary
    images, but that label remains screening unless the examiner explicitly
    confirms that the current evidence belongs to the validation domain.
    """
    path = Path(model_path) if model_path else _default_model_path()
    if path is None:
        return {
            "status": "not_configured",
            "validated": False,
            "warning": "No synthetic-media classifier is available. Set MFLAB_SYNTHETIC_MODEL or install the bundled v0.9 model.",
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
        missing = [n for n in names if n not in values]
        if missing:
            raise KeyError(f"feature schema mismatch; first missing feature={missing[0]}")
        x = np.asarray([[float(values[n]) for n in names]], dtype=float)
        estimator = bundle["estimator"]
        threshold = float(bundle.get("decision_threshold", 0.5))
        probability = None
        if hasattr(estimator, "predict_proba"):
            probability = float(estimator.predict_proba(x)[0, 1])
            raw_score = probability
            pred = int(probability >= threshold)
        elif hasattr(estimator, "decision_function"):
            raw_score = float(estimator.decision_function(x)[0])
            pred = int(estimator.predict(x)[0])
        else:
            pred = int(estimator.predict(x)[0])
            raw_score = float(pred)

        validation = bundle.get("validation", {}) or {}
        calibrated = bool(bundle.get("calibrated", False))
        bundle_validated = bool(bundle.get("validated", False))
        scope = _domain_scope(feature_bank, bundle)
        validated_for_input = bool(
            bundle_validated
            and scope["domain_confirmed_by_examiner"]
            and scope["geometry_match"] is not False
        )
        source = "bundled" if path.resolve() == _builtin_model_path().resolve() else "configured_external"
        return {
            "status": "success",
            "model_name": bundle.get("model_name", path.stem),
            "model_path": str(path),
            "model_source": source,
            "predicted_label": "synthetic" if pred == 1 else "real",
            "score": raw_score,
            "score_synthetic": probability if probability is not None else raw_score,
            "decision_threshold": threshold,
            "calibrated_probability_synthetic": probability if calibrated else None,
            "calibrated": calibrated,
            "bundle_validated": bundle_validated,
            "validated": validated_for_input,
            "validated_for_input": validated_for_input,
            "validation": validation,
            **scope,
            "warning": (
                "The machine label is not an evidentiary conclusion. This model is validated only within its documented domain. "
                "For arbitrary evidence, leave MFLAB_SYNTHETIC_MODEL_DOMAIN_CONFIRMED unset and interpret the output as screening."
            ),
        }
    except Exception as exc:
        return {"status": "error", "validated": False, "error": repr(exc)}
