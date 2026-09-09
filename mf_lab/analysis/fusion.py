from __future__ import annotations


def synthetic_evidence_fusion(methods: dict) -> dict:
    """Conservative cross-family convergence summary, never a fake/real verdict."""
    families: list[str] = []
    notes: list[str] = []
    spectral = methods.get("synthetic_spectral") or {}
    if spectral.get("screening_flags"):
        families.append("spectral")
    face = methods.get("face_artifacts") or {}
    if face.get("screening_flags"):
        families.append("face_region")
    context = methods.get("face_context_consistency") or {}
    if context.get("screening_flags"):
        families.append("face_context")
    noise = methods.get("noise_map") or {}
    if float(noise.get("local_std_cv", 0) or 0) > 0.75:
        families.append("noise_consistency")
    prnu = methods.get("prnu_screen") or {}
    if float(prnu.get("local_energy_cv", 0) or 0) > 0.75:
        families.append("sensor_residual")
    c2pa = methods.get("c2pa") or {}
    if c2pa.get("cryptographically_validated"):
        families.append("validated_provenance")
        notes.append("Cryptographically validated C2PA is provenance evidence, not pixel-classifier evidence.")
    learned = methods.get("synthetic_ml_models") or {}
    for row in learned.get("outputs", []) if isinstance(learned, dict) else []:
        if row.get("status") == "success" and row.get("scientifically_validated") is True:
            families.append("validated_deep_model" if row.get("model_kind") == "deep" else "validated_handcrafted_ml")
    ensemble = methods.get("synthetic_ensemble") or {}
    if ensemble.get("status") == "screening_ensemble" and ensemble.get("model_count", 0):
        notes.append("A calibrated ensemble is summarized separately and is not counted as another independent family.")
    observed = sorted(set(families))
    if len(observed) >= 4:
        level = "high_convergence_for_expert_review"
    elif len(observed) >= 2:
        level = "moderate_convergence_for_expert_review"
    elif len(observed) == 1:
        level = "single_family_observation"
    else:
        level = "no_convergent_signal"
    return {
        "status": "success", "operational_families": observed, "family_count": len(observed),
        "convergence_level": level, "evidentiary_conclusion": "inconclusive", "notes": notes,
        "warning": "Convergence is not a posterior probability. Method families may be statistically correlated; domain validation, provenance and expert interpretation remain required.",
    }
