from __future__ import annotations

from pathlib import Path

from mf_lab.analysis.deepfake import image_deepfake_protocol as legacy_image_protocol
from mf_lab.analysis.deepfake import video_deepfake_protocol as legacy_video_protocol


def image_deepfake_protocol_v2(path: str | Path, precomputed: dict | None = None, external_models: list[dict] | None = None) -> dict:
    precomputed = precomputed or {}
    external_models = external_models or []
    base = legacy_image_protocol(path, precomputed=precomputed, external_models=external_models)
    observations = list(base.get("screening_observations") or [])
    evidence = list(base.get("evidence_families") or [])
    external_validated = int(base.get("validated_external_models", 0) or 0)

    feature_bank = precomputed.get("synthetic_feature_bank") or {}
    face_context = precomputed.get("face_context_consistency") or {}
    if face_context.get("screening_flags"):
        observations.append({"family": "face_context", "signals": face_context.get("screening_flags"), "calibrated": False})

    native_validated = 0
    model_group = precomputed.get("synthetic_ml_models") or {}
    for result in model_group.get("outputs", []) if isinstance(model_group, dict) else []:
        if result.get("status") != "success":
            continue
        row = {
            "family": "deep_detector" if result.get("model_kind") == "deep" else "handcrafted_ml_detector",
            "model": result.get("model"), "score": result.get("score"),
            "probability_synthetic": result.get("probability_synthetic"),
            "calibrated": bool(result.get("calibrated", False)),
            "scientifically_validated": bool(result.get("scientifically_validated", False)),
            "validation": result.get("validation"),
        }
        if result.get("scientifically_validated") is True:
            evidence.append(row); native_validated += 1
        else:
            observations.append(row)

    ensemble = precomputed.get("synthetic_ensemble") or {}
    if ensemble.get("status") == "screening_ensemble":
        observations.append({
            "family": "validated_calibrated_model_ensemble", "signals": ["ensemble_available_for_expert_review"],
            "model_count": ensemble.get("model_count"),
            "ensemble_probability_synthetic": ensemble.get("ensemble_probability_synthetic"),
            "calibrated": True,
            "note": "Ensemble output remains a screening summary and not a forensic posterior probability.",
        })

    fusion = precomputed.get("synthetic_evidence_fusion") or {}
    if fusion.get("family_count", 0):
        observations.append({
            "family": "cross_family_convergence", "signals": [fusion.get("convergence_level")],
            "operational_families": fusion.get("operational_families", []), "calibrated": False,
        })

    base.update({
        "protocol_version": "MFLAB-DF-0.5", "screening_observations": observations, "evidence_families": evidence,
        "validated_external_models": external_validated, "validated_native_models": native_validated,
        "validated_learned_models_total": external_validated + native_validated,
        "feature_bank": {"schema": feature_bank.get("schema"), "feature_count": feature_bank.get("feature_count")} if feature_bank.get("status") == "success" else None,
        "ensemble": ensemble, "evidentiary_conclusion": "inconclusive",
        "decision_policy": "MFLAB-DF-0.5 separates provenance, classical forensics, descriptive features, uncalibrated screening, scientifically validated learned models and calibration. No single score is a forensic verdict; cross-generator/domain validation and case-context convergence are required.",
    })
    if external_validated + native_validated > 0:
        base["triage_assessment"] = "needs_expert_review"
    elif observations:
        base["triage_assessment"] = "screening_observations_only"
    else:
        base["triage_assessment"] = "no_strong_screening_signals"
    return base


def video_deepfake_protocol_v2(path: str | Path, external_models: list[dict] | None = None) -> dict:
    base = legacy_video_protocol(path, external_models=external_models or [])
    base["protocol_version"] = "MFLAB-DF-0.5"
    base["decision_policy"] = "Frame/video scores, temporal consistency, encoding and provenance are separate evidence families. A deepfake conclusion requires independently validated detector/domain performance and expert convergence."
    base["evidentiary_conclusion"] = "inconclusive"
    return base
