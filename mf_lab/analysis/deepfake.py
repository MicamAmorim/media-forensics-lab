from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from .classical import frequency_analysis, noise_map_analysis, resampling_analysis, prnu_screen


def _read_bgr(path: str | Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"unreadable image: {path}")
    return img


def face_artifact_screen(path: str | Path) -> dict:
    """Face-region heuristic measurements, deliberately non-classifying.

    We avoid claims such as blink-rate or biological-anatomy detection unless a
    dedicated validated landmark/temporal model is actually present.
    """
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
        # Boundary sharpness: compare a thin outer ring to face interior.
        ring = max(2, min(w, h) // 16)
        edges = cv2.Canny(crop, 80, 160).astype(np.float32) / 255.0
        border_mask = np.zeros_like(edges, dtype=bool)
        border_mask[:ring, :] = True; border_mask[-ring:, :] = True; border_mask[:, :ring] = True; border_mask[:, -ring:] = True
        boundary_edge_density = float(edges[border_mask].mean()) if np.any(border_mask) else 0.0
        interior_edge_density = float(edges[~border_mask].mean()) if np.any(~border_mask) else 0.0
        rows.append({
            "bbox": [int(x), int(y), int(w), int(h)],
            "laplacian_variance": lap_var,
            "left_right_mean_luminance_asymmetry": illum_asym,
            "boundary_edge_density": boundary_edge_density,
            "interior_edge_density": interior_edge_density,
        })
    return {
        "faces_detected": len(faces),
        "faces_analyzed": len(rows),
        "face_metrics": rows,
        "status": "screening_only",
        "warning": "These are generic face-region measurements, not a validated deepfake classifier. Compression, makeup, lighting and camera processing can dominate them.",
    }


def synthetic_spectral_screen(path: str | Path) -> dict:
    f = frequency_analysis(path)
    # Do not convert heuristics into a probability. We expose signal flags only.
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
        "warning": "Spectral fingerprints are generator- and post-processing-dependent. A flag is not a probability that the image was AI-generated.",
    }


def image_deepfake_protocol(path: str | Path, precomputed: dict | None = None, external_models: list[dict] | None = None) -> dict:
    """Multi-family synthetic/deepfake screening protocol for still images.

    The protocol is designed for forensic discipline rather than a single
    'AI score'. It records independent evidence families and leaves the
    evidentiary conclusion inconclusive unless a qualified examiner combines
    validated model outputs, provenance and case context.
    """
    precomputed = precomputed or {}
    external_models = external_models or []
    spectral = precomputed.get("synthetic_spectral") or synthetic_spectral_screen(path)
    face = precomputed.get("face_artifacts") or face_artifact_screen(path)
    noise = precomputed.get("noise_map") or noise_map_analysis(path)
    resampling = precomputed.get("resampling") or resampling_analysis(path)
    prnu = precomputed.get("prnu_screen") or prnu_screen(path)

    evidence = []
    if spectral.get("screening_flags"):
        evidence.append({"family": "frequency", "signals": spectral["screening_flags"], "strength": "screening"})
    if noise.get("local_std_cv", 0) > 0.75:
        evidence.append({"family": "noise_consistency", "signals": ["high_local_residual_variability"], "strength": "screening"})
    if resampling.get("max_nonzero_autocorrelation", 0) > 0.35:
        evidence.append({"family": "resampling", "signals": ["periodic_second_derivative_autocorrelation"], "strength": "screening"})
    if prnu.get("local_energy_cv", 0) > 0.75:
        evidence.append({"family": "sensor_residual", "signals": ["high_local_residual_energy_variability"], "strength": "screening"})

    validated_model_outputs = []
    for model in external_models:
        if model.get("validated") is True and model.get("score") is not None:
            validated_model_outputs.append(model)

    if evidence or validated_model_outputs:
        triage = "needs_expert_review"
    else:
        triage = "no_strong_screening_signals"

    return {
        "protocol_version": "MFLAB-DF-0.2",
        "media_type": "image",
        "stages": [
            "integrity_and_provenance",
            "metadata_and_encoding",
            "classical_image_forensics",
            "face_region_screening_when_applicable",
            "synthetic_frequency_screening",
            "validated_external_model_ensemble_when_configured",
            "manual_cross-method_review",
        ],
        "evidence_families": evidence,
        "external_models": external_models,
        "validated_external_models": len(validated_model_outputs),
        "triage_assessment": triage,
        "evidentiary_conclusion": "inconclusive",
        "decision_policy": "Do not label authentic/AI-generated from a single heuristic or classifier. Seek convergence across independent evidence families and provenance/context.",
        "limitations": [
            "Unknown generators and domain shift can defeat learned detectors.",
            "JPEG recompression, screenshots and social networks may erase or create artifacts.",
            "A real image may be locally AI-edited; a synthetic image may be post-processed to mimic camera statistics.",
            "Absence of detected artifacts is not proof of authenticity.",
        ],
    }


def video_deepfake_screen(path: str | Path, samples: int = 24) -> dict:
    """Temporal face/frequency consistency screening for video.

    This is not a deep-learning detector. It measures sample-to-sample changes
    that may justify escalation to a validated video detector (e.g. a
    DeepfakeBench video model) and manual frame review.
    """
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
            face_metric = {
                "bbox": [int(x), int(y), int(w), int(h)],
                "sharpness": float(cv2.Laplacian(crop, cv2.CV_32F).var()),
                "mean_luminance": float(crop.mean()),
            }
        # simple frame spectral ratio
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
    metrics = {
        "sampled_frames": len(rows),
        "frames_with_face": sum(1 for r in rows if r["face"]),
        "face_sharpness_cv": cv(sharp),
        "face_luminance_cv": cv(lum),
        "spectral_ratio_cv": cv(ratios),
    }
    flags = []
    if metrics["face_sharpness_cv"] is not None and metrics["face_sharpness_cv"] > 1.0:
        flags.append("large_face_texture_sharpness_variation")
    if metrics["spectral_ratio_cv"] is not None and metrics["spectral_ratio_cv"] > 0.75:
        flags.append("large_sampled_frequency_variation")
    return {
        "status": "screening_only",
        "metrics": metrics,
        "screening_flags": flags,
        "samples": rows,
        "triage_assessment": "needs_expert_review" if flags else "no_strong_screening_signals",
        "evidentiary_conclusion": "inconclusive",
        "warning": "Escalate suspicious cases to validated frame/video deepfake models and manual temporal review. This module does not infer blinking or micro-expressions.",
    }


def video_deepfake_protocol(path: str | Path, external_models: list[dict] | None = None) -> dict:
    """Forensic wrapper around temporal screening + optional validated models."""
    external_models = external_models or []
    screen = video_deepfake_screen(path)
    validated = [m for m in external_models if m.get("validated") is True and m.get("score") is not None]
    evidence = []
    if screen.get("screening_flags"):
        evidence.append({
            "family": "temporal_frequency_face_consistency",
            "signals": screen.get("screening_flags", []),
            "strength": "screening",
        })
    for m in validated:
        evidence.append({
            "family": "validated_learned_detector",
            "model": m.get("model") or m.get("name"),
            "score": m.get("score"),
            "label": m.get("label"),
            "validation": m.get("validation") or m.get("protocol"),
            "strength": "model_output_requires_case_interpretation",
        })
    return {
        "protocol_version": "MFLAB-DF-0.2",
        "media_type": "video",
        "stages": [
            "integrity_and_provenance",
            "container_codec_timestamps_and_gop",
            "frame_sampling_and_temporal_consistency_screening",
            "validated_external_video_detector_ensemble_when_configured",
            "manual_frame_sequence_review",
            "cross_method_and_contextual_convergence",
        ],
        "native_screen": screen,
        "external_models": external_models,
        "validated_external_models": len(validated),
        "evidence_families": evidence,
        "triage_assessment": "needs_expert_review" if evidence else "no_strong_screening_signals",
        "evidentiary_conclusion": "inconclusive",
        "decision_policy": "No single frame-level or video-level score is converted into a forensic conclusion. Validate detector/domain and seek convergence with provenance, encoding, temporal and contextual evidence.",
        "limitations": [
            "Frame sampling may miss short manipulated intervals.",
            "Compression and transcoding can mask or create temporal/frequency artifacts.",
            "Detector performance may collapse under domain shift or unseen generators.",
            "Absence of a detected artifact is not proof of authenticity.",
        ],
    }
