from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from .classical import frequency_analysis, noise_map_analysis, resampling_analysis, prnu_screen
from .c2pa import c2pa_inspect
from mf_lab.utils.io import cv_imread


def _read_bgr(path: str | Path) -> np.ndarray:
    img = cv_imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"unreadable image: {path}")
    return img


def face_artifact_screen(path: str | Path) -> dict:
    """Face-region heuristic measurements, deliberately non-classifying."""
    bgr = _read_bgr(path)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48)) if not cascade.empty() else []
    rows = []
    for (x, y, w, h) in faces[:10]:
        crop = gray[y:y + h, x:x + w]
        lap_var = float(cv2.Laplacian(crop, cv2.CV_32F).var())
        left = crop[:, :max(1, w // 2)]
        right = crop[:, w // 2:]
        illum_asym = abs(float(left.mean()) - float(right.mean())) / 255.0 if right.size else 0.0
        ring = max(2, min(w, h) // 16)
        edges = cv2.Canny(crop, 80, 160).astype(np.float32) / 255.0
        border_mask = np.zeros_like(edges, dtype=bool)
        border_mask[:ring, :] = True; border_mask[-ring:, :] = True; border_mask[:, :ring] = True; border_mask[:, -ring:] = True
        boundary_edge_density = float(edges[border_mask].mean()) if np.any(border_mask) else 0.0
        interior_edge_density = float(edges[~border_mask].mean()) if np.any(~border_mask) else 0.0
        edge_ratio = boundary_edge_density / (interior_edge_density + 1e-12)
        flags = []
        if edge_ratio >= 1.15 and lap_var < 700.0:
            flags.append("face_boundary_texture_discontinuity")
        if illum_asym >= 0.12 and lap_var < 700.0:
            flags.append("face_luminance_texture_inconsistency")
        rows.append({
            "bbox": [int(x), int(y), int(w), int(h)],
            "laplacian_variance": lap_var,
            "left_right_mean_luminance_asymmetry": illum_asym,
            "boundary_edge_density": boundary_edge_density,
            "interior_edge_density": interior_edge_density,
            "boundary_interior_edge_ratio": float(edge_ratio),
            "screening_flags": flags,
        })
    all_flags = sorted({flag for row in rows for flag in row.get("screening_flags", [])})
    return {
        "faces_detected": len(faces),
        "faces_analyzed": len(rows),
        "face_metrics": rows,
        "screening_flags": all_flags,
        "status": "screening_only",
        "calibrated": False,
        "warning": "Generic face-region measurements and engineering thresholds are screening only, not a validated deepfake classifier. Compression, makeup, lighting and camera processing can dominate them.",
    }


def synthetic_spectral_screen(path: str | Path) -> dict:
    f = frequency_analysis(path)
    flags = []
    if f.get("spectral_peak_count", 0) >= 4:
        flags.append("multiple_radial_spectral_peaks")
    ratio = f.get("high_low_frequency_ratio")
    if ratio is not None and (ratio < 0.30 or ratio > 1.25):
        flags.append("unusual_high_low_frequency_ratio")
    qcv = f.get("quadrant_mean_cv")
    if qcv is not None and qcv < 0.01:
        flags.append("high_spectral_quadrant_symmetry")
    return {
        "features": f,
        "screening_flags": flags,
        "status": "screening_only",
        "calibrated": False,
        "warning": "Spectral fingerprints are generator- and post-processing-dependent. These flags are uncalibrated observations and are not a probability that the image was AI-generated.",
    }


def image_deepfake_protocol(path: str | Path, precomputed: dict | None = None, external_models: list[dict] | None = None) -> dict:
    precomputed = precomputed or {}
    external_models = external_models or []
    spectral = precomputed.get("synthetic_spectral") or synthetic_spectral_screen(path)
    face = precomputed.get("face_artifacts") or face_artifact_screen(path)
    c2pa = precomputed.get("c2pa") or c2pa_inspect(path)
    noise = precomputed.get("noise_map") or noise_map_analysis(path)
    resampling = precomputed.get("resampling") or resampling_analysis(path)
    prnu = precomputed.get("prnu_screen") or prnu_screen(path)

    screening_observations = []
    if spectral.get("screening_flags"):
        screening_observations.append({"family": "frequency", "signals": spectral["screening_flags"], "calibrated": False})
    if face.get("screening_flags"):
        screening_observations.append({"family": "face_region", "signals": face["screening_flags"], "calibrated": False})
    if c2pa.get("embedded_c2pa_marker_present"):
        screening_observations.append({
            "family": "content_provenance",
            "signals": ["embedded_c2pa_manifest_marker"],
            "producer_hint": c2pa.get("producer_hint"),
            "cryptographically_validated": bool(c2pa.get("cryptographically_validated")),
            "calibrated": False,
        })
    if noise.get("local_std_cv", 0) > 0.75:
        screening_observations.append({"family": "noise_consistency", "signals": ["high_local_residual_variability"], "calibrated": False})
    if resampling.get("screening_flag") is True:
        screening_observations.append({"family": "resampling", "signals": ["short_lag_derivative_persistence"], "calibrated": False})
    spectral_features = spectral.get("features", {}) if isinstance(spectral.get("features"), dict) else {}
    spectral_ratio = spectral_features.get("high_low_frequency_ratio")
    prnu_std = prnu.get("residual_std") if isinstance(prnu, dict) else None
    if spectral_ratio is not None and prnu_std is not None and spectral_ratio < 0.55 and prnu_std < 0.02:
        screening_observations.append({
            "family": "synthetic_texture",
            "signals": ["low_high_frequency_ratio_with_low_sensor_residual"],
            "high_low_frequency_ratio": spectral_ratio,
            "prnu_like_residual_std": prnu_std,
            "calibrated": False,
            "scope": "engineering threshold regression-tested on bundled synthetic fixture only",
        })
    if prnu.get("local_energy_cv", 0) > 0.75:
        screening_observations.append({"family": "sensor_residual", "signals": ["high_local_residual_energy_variability"], "calibrated": False})

    validated_model_outputs = []
    evidence = []
    for model in external_models:
        if model.get("validated") is True and model.get("score") is not None:
            validated_model_outputs.append(model)
            evidence.append({
                "family": "validated_learned_detector",
                "model": model.get("model") or model.get("name"),
                "score": model.get("score"),
                "label": model.get("label"),
                "validation": model.get("validation") or model.get("dataset") or model.get("protocol"),
                "strength": "model_output_requires_case_interpretation",
            })

    if validated_model_outputs:
        triage = "needs_expert_review"
    elif screening_observations:
        triage = "screening_observations_only"
    else:
        triage = "no_strong_screening_signals"

    return {
        "protocol_version": "MFLAB-DF-0.4",
        "media_type": "image",
        "stages": [
            "integrity_and_provenance", "metadata_and_encoding", "classical_image_forensics",
            "face_region_screening_when_applicable", "synthetic_frequency_screening",
            "content_credentials_provenance_screening", "validated_external_model_ensemble_when_configured",
            "manual_cross-method_review",
        ],
        "screening_observations": screening_observations,
        "evidence_families": evidence,
        "external_models": external_models,
        "validated_external_models": len(validated_model_outputs),
        "triage_assessment": triage,
        "evidentiary_conclusion": "inconclusive",
        "decision_policy": "Uncalibrated native heuristics and marker-only provenance are observations only and cannot trigger a deepfake-specific evidentiary conclusion. Cryptographically validated Content Credentials may provide provenance evidence, while learned-detector claims still require documented domain validation and contextual convergence.",
        "limitations": [
            "Unknown generators and domain shift can defeat learned detectors.",
            "JPEG recompression, screenshots and social networks may erase or create artifacts.",
            "A real image may be locally AI-edited; a synthetic image may be post-processed to mimic camera statistics.",
            "Absence of detected artifacts is not proof of authenticity.",
        ],
    }


def video_deepfake_screen(path: str | Path, samples: int = 24) -> dict:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"status": "error", "error": "could_not_open_video"}
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if n <= 0:
        cap.release(); return {"status": "error", "error": "unknown_frame_count"}
    indices = np.unique(np.linspace(0, max(0, n - 1), min(samples, n)).astype(int))
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    rows = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if not ok:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(48, 48)) if not cascade.empty() else []
        face_metric = None
        if len(faces):
            x, y, w, h = max(faces, key=lambda z: z[2] * z[3])
            crop = gray[y:y + h, x:x + w]
            face_metric = {"bbox": [int(x), int(y), int(w), int(h)], "sharpness": float(cv2.Laplacian(crop, cv2.CV_32F).var()), "mean_luminance": float(crop.mean())}
        small = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA).astype(np.float32)
        dct = cv2.dct(small)
        low = float(np.mean(np.abs(dct[:64, :64])))
        high = float(np.mean(np.abs(dct[128:, 128:])))
        rows.append({"frame_index": int(idx), "face_count": int(len(faces)), "face": face_metric, "hf_lf_dct_ratio": high / (low + 1e-12)})
    cap.release()
    sharp = [r["face"]["sharpness"] for r in rows if r["face"]]
    lum = [r["face"]["mean_luminance"] for r in rows if r["face"]]
    ratios = [r["hf_lf_dct_ratio"] for r in rows]
    def cv(vals):
        return float(np.std(vals) / (np.mean(vals) + 1e-12)) if vals else None
    metrics = {"sampled_frames": len(rows), "frames_with_face": sum(1 for r in rows if r["face"]), "face_sharpness_cv": cv(sharp), "face_luminance_cv": cv(lum), "spectral_ratio_cv": cv(ratios)}
    flags = []
    if metrics["face_sharpness_cv"] is not None and metrics["face_sharpness_cv"] > 1.0:
        flags.append("large_face_texture_sharpness_variation")
    if metrics["spectral_ratio_cv"] is not None and metrics["spectral_ratio_cv"] > 0.75:
        flags.append("large_sampled_frequency_variation")
    return {"status": "screening_only", "metrics": metrics, "screening_flags": flags, "samples": rows,
            "triage_assessment": "needs_expert_review" if flags else "no_strong_screening_signals",
            "evidentiary_conclusion": "inconclusive",
            "warning": "Escalate suspicious cases to validated frame/video deepfake models and manual temporal review. This module does not infer blinking or micro-expressions."}


def video_deepfake_protocol(path: str | Path, external_models: list[dict] | None = None) -> dict:
    external_models = external_models or []
    screen = video_deepfake_screen(path)
    validated = [m for m in external_models if m.get("validated") is True and m.get("score") is not None]
    evidence = []
    if screen.get("screening_flags"):
        evidence.append({"family": "temporal_frequency_face_consistency", "signals": screen.get("screening_flags", []), "strength": "screening"})
    for m in validated:
        evidence.append({"family": "validated_learned_detector", "model": m.get("model") or m.get("name"), "score": m.get("score"),
                         "label": m.get("label"), "validation": m.get("validation") or m.get("protocol"),
                         "strength": "model_output_requires_case_interpretation"})
    return {
        "protocol_version": "MFLAB-DF-0.4", "media_type": "video",
        "stages": ["integrity_and_provenance", "container_codec_timestamps_and_gop", "frame_sampling_and_temporal_consistency_screening",
                   "validated_external_video_detector_ensemble_when_configured", "manual_frame_sequence_review", "cross_method_and_contextual_convergence"],
        "native_screen": screen, "external_models": external_models, "validated_external_models": len(validated),
        "evidence_families": evidence, "triage_assessment": "needs_expert_review" if evidence else "no_strong_screening_signals",
        "evidentiary_conclusion": "inconclusive",
        "decision_policy": "No single frame-level or video-level score is converted into a forensic conclusion. Validate detector/domain and seek convergence with provenance, encoding, temporal and contextual evidence.",
        "limitations": ["Frame sampling may miss short manipulated intervals.", "Compression and transcoding can mask or create temporal/frequency artifacts.",
                        "Detector performance may collapse under domain shift or unseen generators.", "Absence of a detected artifact is not proof of authenticity."],
    }
