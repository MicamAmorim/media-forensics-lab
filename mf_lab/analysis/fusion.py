from __future__ import annotations


def synthetic_evidence_fusion(methods: dict) -> dict:
    """Conservative cross-family convergence summary, not a fake/real verdict."""
    families = []
    notes = []

    spectral = methods.get("synthetic_spectral") or {}
    if spectral.get("screening_flags"):
        families.append("spectral")
    face = methods.get("face_artifacts") or {}
    if face.get("screening_flags"):
        families.append("face")
    context = methods.get("face_context_consistency") or {}
    if context.get("screening_flags"):
        families.append("face_context")
    noise = methods.get("noise_map") or {}
    if float(noise.get("local_std_cv", 0) or 0) > 0.75:
        families.append("noise")
    prnu = methods.get("prnu_screen") or {}
    if float(prnu.get("local_energy_cv", 0) or 0) > 0.75:
        families.append("sensor_residual")
    c2pa = methods.get("c2pa") or {}
    if c2pa.get("cryptographically_validated"):
        families.append("validated_provenance")
        notes.append("C2PA cryptographic validation is provenance evidence, not pixel-classifier evidence.")

    for key, family in (
        ("synthetic_ml", "handcrafted_ml"),
        ("synthetic_deep", "deep_model"),
        ("autogan_classifier", "autogan_spectral_model"),
    ):
        r = methods.get(key) or {}
        if r.get("status") == "success" and r.get("validated") is True:
            families.append(family)

    autogan = methods.get("autogan_spectral") or {}
    if autogan.get("status") == "success":
        notes.append(
            "AutoGAN-compatible descriptors target GAN upsampling artifacts. Their execution alone is descriptive and does not create an independent evidence family."
        )

    independent = sorted(set(families))
    if len(independent) >= 4:
        level = "high_convergence_for_expert_review"
    elif len(independent) >= 2:
        level = "moderate_convergence_for_expert_review"
    elif len(independent) == 1:
        level = "single_family_observation"
    else:
        level = "no_convergent_signal"
    return {
        "status": "success",
        "independent_families": independent,
        "family_count": len(independent),
        "convergence_level": level,
        "evidentiary_conclusion": "inconclusive",
        "notes": notes,
        "warning": "Convergence is a review-prioritization summary. It is not a posterior probability and does not replace validation, provenance or expert interpretation.",
    }
