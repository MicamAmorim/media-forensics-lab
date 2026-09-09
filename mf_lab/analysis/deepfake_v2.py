from __future__ import annotations

from pathlib import Path

from mf_lab.analysis.deepfake import image_deepfake_protocol as legacy_image_protocol
from mf_lab.analysis.deepfake import video_deepfake_protocol as legacy_video_protocol


def image_deepfake_protocol_v2(path: str | Path, precomputed: dict | None = None, external_models: list[dict] | None = None) -> dict:
    precomputed = precomputed or {}
    base = legacy_image_protocol(path, precomputed=precomputed, external_models=external_models or [])
    observations = list(base.get("screening_observations") or [])
    evidence = list(base.get("evidence_families") or [])

    face_context = precomputed.get("face_context_consistency") or {}
    if face_context.get("screening_flags"):
        observations.append({
            "family": "face_context",
            "signals": face_context.get("screening_flags"),
            "calibrated": False,
        })

    for key, family in (("synthetic_ml", "handcrafted_ml_detector"), ("synthetic_deep", "deep_detector")):
        result = precomputed.get(key) or {}
        if result.get("status") == "success":
            score = result.get("score", result.get("score_synthetic"))
            row = {
                "family": family,
                "model": result.get("model_name"),
                "score": score,
                "calibrated": bool(result.get("calibrated", False)),
                "validated": bool(result.get("validated", False)),
            }
            if result.get("validated") is True:
                evidence.append(row)
            elif result.get("predicted_label") == "synthetic" or (isinstance(score, (int, float)) and float(score) >= 0.5):
                observations.append(row)

    fusion = precomputed.get("synthetic_evidence_fusion") or {}
    if fusion.get("family_count", 0):
        observations.append({
            "family": "cross_family_convergence",
            "signals": [fusion.get("convergence_level")],
            "independent_families": fusion.get("independent_families", []),
            "calibrated": False,
        })

    base["protocol_version"] = "MFLAB-DF-0.5"
    base["screening_observations"] = observations
    base["evidence_families"] = evidence
    base["validated_external_models"] = len([
        x for x in evidence
        if x.get("validated") is True or x.get("family") == "validated_learned_detector"
    ])
    if evidence:
        base["triage_assessment"] = "needs_expert_review"
    elif observations:
        base["triage_assessment"] = "screening_observations_only"
    else:
        base["triage_assessment"] = "no_strong_screening_signals"
    base["evidentiary_conclusion"] = "inconclusive"
    base["decision_policy"] = (
        "MFLAB-DF-0.5 separates descriptive forensic features, uncalibrated screening, validated learned models and provenance. "
        "No single score is a forensic verdict; cross-generator/domain validation and case-context convergence are required."
    )
    return base


def video_deepfake_protocol_v2(path: str | Path, external_models: list[dict] | None = None) -> dict:
    base = legacy_video_protocol(path, external_models=external_models or [])
    base["protocol_version"] = "MFLAB-DF-0.5"
    base["decision_policy"] = (
        "Frame/video scores, temporal consistency, encoding and provenance are separate evidence families. "
        "A deepfake conclusion requires validated detector/domain performance and expert convergence."
    )
    return base
