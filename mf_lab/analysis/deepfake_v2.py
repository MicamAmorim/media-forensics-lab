from __future__ import annotations

from pathlib import Path

from mf_lab.analysis.deepfake import image_deepfake_protocol as legacy_image_protocol
from mf_lab.analysis.deepfake import video_deepfake_protocol as legacy_video_protocol


def _machine_assessment(precomputed: dict) -> dict:
    ml = precomputed.get("synthetic_ml") or {}
    if ml.get("status") != "success":
        return {
            "status": "unavailable",
            "reason": ml.get("status", "not_available"),
            "label": None,
            "forensic_effect": "none",
        }
    score = ml.get("calibrated_probability_synthetic")
    if score is None:
        score = ml.get("score_synthetic", ml.get("score"))
    validated_for_input = bool(ml.get("validated_for_input", ml.get("validated", False)))
    return {
        "status": "available",
        "label": ml.get("predicted_label"),
        "score_synthetic": score,
        "decision_threshold": ml.get("decision_threshold", 0.5),
        "model_name": ml.get("model_name"),
        "model_source": ml.get("model_source"),
        "calibrated": bool(ml.get("calibrated", False)),
        "model_validated_in_declared_domain": bool(ml.get("bundle_validated", ml.get("validated", False))),
        "validated_for_input": validated_for_input,
        "validation_scope_status": ml.get("validation_scope_status"),
        "declared_validation_domain": ml.get("declared_validation_domain"),
        "expected_resolution": ml.get("expected_resolution"),
        "observed_resolution": ml.get("observed_resolution"),
        "forensic_effect": "validated_model_evidence" if validated_for_input else "screening_only",
        "interpretation": (
            "Automatic computational classification only. It is intentionally separate from the evidentiary conclusion; "
            "a real/synthetic label is not by itself a forensic verdict."
        ),
    }


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

    autogan_spectral = precomputed.get("autogan_spectral") or {}
    if autogan_spectral.get("screening_flags"):
        observations.append({
            "family": "autogan_spectral_descriptors",
            "signals": autogan_spectral.get("screening_flags"),
            "calibrated": False,
            "validated": False,
            "scope": autogan_spectral.get("method_scope"),
        })

    for key, family in (
        ("synthetic_ml", "handcrafted_ml_detector"),
        ("synthetic_deep", "deep_detector"),
        ("autogan_classifier", "autogan_spectral_detector"),
    ):
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
            if result.get("method_scope"):
                row["scope"] = result.get("method_scope")
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

    base["protocol_version"] = "MFLAB-DF-0.7"
    base["screening_observations"] = observations
    base["evidence_families"] = evidence
    base["machine_assessment"] = _machine_assessment(precomputed)
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
        "MFLAB-DF-0.7 separates the machine real/synthetic assessment from the forensic evidentiary conclusion. "
        "The bundled CIFAKE classifier may produce an automatic label, but it is treated as screening outside its declared validation domain. "
        "Descriptive forensic features, AutoGAN-compatible GAN spectral descriptors, uncalibrated screening, validated learned models and provenance remain separate. "
        "No single score is a forensic verdict; cross-generator/domain validation and case-context convergence are required. "
        "A negative GAN-spectral result does not exclude diffusion or other synthetic-media families."
    )
    return base


def video_deepfake_protocol_v2(path: str | Path, external_models: list[dict] | None = None) -> dict:
    base = legacy_video_protocol(path, external_models=external_models or [])
    base["protocol_version"] = "MFLAB-DF-0.7"
    base["decision_policy"] = (
        "Frame/video scores, temporal consistency, encoding and provenance are separate evidence families. "
        "A deepfake conclusion requires validated detector/domain performance and expert convergence."
    )
    return base
