from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from mf_lab.analysis.autogan_spectral import autogan_spectral_analysis
from mf_lab.analysis.c2pa import c2pa_inspect
from mf_lab.analysis.classical import (
    frequency_analysis,
    histogram_analysis,
    jpeg_ghost_analysis,
    jpeg_quantization_analysis,
    lsb_steganography_screen,
    noise_map_analysis,
    perceptual_hashes,
    prnu_screen,
    resampling_analysis,
)
from mf_lab.analysis.deepfake import face_artifact_screen, synthetic_spectral_screen
from mf_lab.analysis.deepfake_v2 import image_deepfake_protocol_v2, video_deepfake_protocol_v2
from mf_lab.analysis.face_context import face_context_consistency
from mf_lab.analysis.fusion import synthetic_evidence_fusion
from mf_lab.analysis.image import copy_move_orb, ela, jpeg_dct_periodicity, noise_residual_stats
from mf_lab.analysis.metadata import image_metadata, video_metadata
from mf_lab.analysis.reference import reference_image_difference, reference_video_sequence_alignment
from mf_lab.analysis.synthetic_deep import score_synthetic_onnx
from mf_lab.analysis.synthetic_features import extract_synthetic_feature_bank
from mf_lab.analysis.synthetic_ml import score_synthetic_ml
from mf_lab.analysis.video import frame_hash_duplicates, frame_timing, frame_transition_anomalies, motion_discontinuity_screen
from mf_lab.autogan_visuals import generate_autogan_visual_artifacts
from mf_lab.integrations.autogan import score_autogan_checkpoint, status as autogan_status
from mf_lab.integrations.external import load_case_external_models
from mf_lab.integrations.veritas import run_all as run_veritas_all, status as veritas_status
from mf_lab.utils.io import sha256, write_json
from mf_lab.version import current_version
from mf_lab.visual_artifacts import generate_visual_artifacts

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp", ".heic", ".heif"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mts", ".m2ts"}

METHODS = {
    "hash_sha256": {"refs": ["cpp_chain_custody", "swgde_integrity"]},
    "perceptual_hashes": {"refs": ["farid_photo_forensics"], "screening_only": True},
    "c2pa": {"refs": ["c2pa_2_4"]},
    "metadata": {"refs": ["swgde_image_auth", "swgde_video_auth"]},
    "ela": {"refs": ["farid_photo_forensics"], "screening_only": True},
    "histogram": {"refs": ["farid_photo_forensics"], "screening_only": True},
    "noise_residual": {"refs": ["verdoliva_2020", "trufor_2023"], "screening_only": True},
    "noise_map": {"refs": ["verdoliva_2020", "trufor_2023"], "screening_only": True},
    "jpeg_ghost": {"refs": ["farid_photo_forensics", "lukas_fridrich_2003"], "screening_only": True},
    "jpeg_quantization": {"refs": ["lukas_fridrich_2003"], "screening_only": True},
    "jpeg_dct": {"refs": ["lukas_fridrich_2003"], "screening_only": True},
    "copy_move_orb": {"refs": ["fridrich_soukal_lukas_2003"], "screening_only": True},
    "frequency": {"refs": ["verdoliva_2020", "durall_2020", "say_alkan_kocak_2025"], "screening_only": True},
    "resampling": {"refs": ["popescu_farid_2005"], "screening_only": True},
    "steganography_lsb": {"refs": ["fridrich_steganography_2010"], "screening_only": True},
    "prnu_screen": {"refs": ["lukas_fridrich_goljan_2005"], "screening_only": True},
    "face_artifacts": {"refs": ["verdoliva_2020", "faceforensics_2019"], "screening_only": True},
    "face_context_consistency": {"refs": ["verdoliva_2020", "faceforensics_2019", "sao_2025"], "screening_only": True},
    "synthetic_spectral": {"refs": ["verdoliva_2020", "durall_2020", "say_alkan_kocak_2025"], "screening_only": True},
    "autogan_spectral": {"refs": ["autogan_2019", "durall_2020"], "screening_only": True},
    "autogan_classifier": {"refs": ["autogan_2019"], "model_based": True},
    "synthetic_feature_bank": {"refs": ["durall_2020", "cifake_2023", "say_alkan_kocak_2025"], "screening_only": True},
    "synthetic_ml": {"refs": ["cifake_2023", "deepfakebench_2023", "say_alkan_kocak_2025"], "model_based": True},
    "synthetic_deep": {"refs": ["deepfakebench_2023", "faceforensics_2019", "celebdf_2020", "wyawahare_2025", "sao_2025"], "model_based": True},
    "synthetic_evidence_fusion": {"refs": ["verdoliva_2020", "deepfakebench_2023", "say_alkan_kocak_2025", "autogan_2019"], "screening_only": True},
    "deepfake_protocol": {"refs": ["verdoliva_2020", "deepfakebench_2023", "faceforensics_2019", "celebdf_2020", "durall_2020", "autogan_2019", "say_alkan_kocak_2025", "wyawahare_2025", "sao_2025"]},
    "video_timing": {"refs": ["swgde_video_auth", "swgde_ffmpeg"]},
    "video_duplicates": {"refs": ["swgde_video_auth"], "screening_only": True},
    "video_transition_anomalies": {"refs": ["swgde_video_auth"], "screening_only": True},
    "video_motion_discontinuities": {"refs": ["swgde_video_auth"], "screening_only": True},
    "reference_image_difference": {"refs": ["swgde_image_auth"], "screening_only": True, "reference_assisted": True},
    "reference_video_alignment": {"refs": ["swgde_video_auth"], "screening_only": True, "reference_assisted": True},
    "video_deepfake_protocol": {"refs": ["swgde_video_auth", "deepfakebench_2023", "faceforensics_2019", "celebdf_2020"]},
    "veritas_upstream_crosscheck": {"refs": ["veritas_2025"], "screening_only": True, "secondary_implementation": True},
}

PROFILES = {
    "quick": "Integrity/provenance + metadata + compact classical/deepfake screening.",
    "deepfake": "Full synthetic/deepfake protocol with handcrafted features, AutoGAN-compatible spectral analysis and optional validated ML/deep models.",
    "full": "All native image/video screening methods plus synthetic-media protocol and AutoGAN-compatible spectral analysis.",
}


def _environment() -> dict:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "mflab_version": current_version(),
        "veritas_integration": veritas_status(),
        "autogan_integration": autogan_status(),
    }


def _safe_method(methods: dict, name: str, fn, *args, **kwargs) -> None:
    try:
        methods[name] = fn(*args, **kwargs)
    except Exception as e:
        methods[name] = {"status": "error", "error": repr(e)}


def _merge_visual_artifacts(base: dict, extra: dict) -> dict:
    if not isinstance(base, dict):
        base = {"status": "no_artifacts", "artifact_count": 0, "items": [], "errors": []}
    base.setdefault("items", [])
    base.setdefault("errors", [])
    base["items"].extend(extra.get("items") or [])
    base["errors"].extend(extra.get("errors") or [])
    base["artifact_count"] = len(base["items"])
    if base["items"]:
        base["status"] = "success"
    base["autogan"] = {
        "status": extra.get("status"),
        "artifact_count": int(extra.get("artifact_count", 0) or 0),
    }
    return base


def analyze_file(path: str | Path, out_dir: str | Path, profile: str = "full",
                 case_dir: str | Path | None = None, run_veritas: bool = False,
                 reference_path: str | Path | None = None) -> dict:
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}; choose one of {', '.join(PROFILES)}")
    path = Path(path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()
    is_video = ext in VIDEO_EXTS
    is_image = ext in IMAGE_EXTS or not is_video
    external_models = load_case_external_models(case_dir, path.name) if case_dir else []
    report = {
        "schema_version": "0.7",
        "file": str(path),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "environment": _environment(),
        "methods": {},
    }
    m = report["methods"]
    m["hash_sha256"] = {"sha256": report["sha256"]}
    _safe_method(m, "c2pa", c2pa_inspect, path)

    if is_video:
        _safe_method(m, "metadata", video_metadata, path)
        _safe_method(m, "video_timing", frame_timing, path)
        _safe_method(m, "video_duplicates", frame_hash_duplicates, path)
        _safe_method(m, "video_transition_anomalies", frame_transition_anomalies, path)
        _safe_method(m, "video_motion_discontinuities", motion_discontinuity_screen, path)
        if reference_path is not None:
            _safe_method(m, "reference_video_alignment", reference_video_sequence_alignment, path, reference_path)
        _safe_method(m, "video_deepfake_protocol", video_deepfake_protocol_v2, path, external_models)
    elif is_image:
        _safe_method(m, "metadata", image_metadata, path)
        _safe_method(m, "perceptual_hashes", perceptual_hashes, path)
        _safe_method(m, "ela", ela, path)
        _safe_method(m, "noise_residual", noise_residual_stats, path)
        _safe_method(m, "noise_map", noise_map_analysis, path)
        if profile in {"deepfake", "full"}:
            _safe_method(m, "histogram", histogram_analysis, path)
            _safe_method(m, "frequency", frequency_analysis, path)
            _safe_method(m, "resampling", resampling_analysis, path)
            _safe_method(m, "prnu_screen", prnu_screen, path)
            _safe_method(m, "face_artifacts", face_artifact_screen, path)
            _safe_method(m, "face_context_consistency", face_context_consistency, path)
            _safe_method(m, "synthetic_spectral", synthetic_spectral_screen, path)
            _safe_method(m, "autogan_spectral", autogan_spectral_analysis, path)
            _safe_method(m, "synthetic_feature_bank", extract_synthetic_feature_bank, path)
            _safe_method(m, "synthetic_ml", score_synthetic_ml, m.get("synthetic_feature_bank", {}))
            _safe_method(m, "synthetic_deep", score_synthetic_onnx, path)
            _safe_method(m, "autogan_classifier", score_autogan_checkpoint, path)
        if ext in {".jpg", ".jpeg"}:
            _safe_method(m, "jpeg_quantization", jpeg_quantization_analysis, path)
            if profile in {"deepfake", "full"}:
                _safe_method(m, "jpeg_ghost", jpeg_ghost_analysis, path)
                _safe_method(m, "jpeg_dct", jpeg_dct_periodicity, path)
        if profile == "full":
            _safe_method(m, "copy_move_orb", copy_move_orb, path)
            _safe_method(m, "steganography_lsb", lsb_steganography_screen, path)
        if reference_path is not None:
            _safe_method(m, "reference_image_difference", reference_image_difference, path, reference_path)
        if profile in {"deepfake", "full"}:
            _safe_method(m, "synthetic_evidence_fusion", synthetic_evidence_fusion, m)
        precomputed = {k: m.get(k) for k in (
            "c2pa", "noise_map", "resampling", "prnu_screen", "face_artifacts",
            "face_context_consistency", "synthetic_spectral", "autogan_spectral",
            "synthetic_feature_bank", "synthetic_ml", "synthetic_deep", "autogan_classifier",
            "synthetic_evidence_fusion",
        )}
        _safe_method(m, "deepfake_protocol", image_deepfake_protocol_v2, path, precomputed, external_models)
        if run_veritas:
            _safe_method(m, "veritas_upstream_crosscheck", run_veritas_all, path)

    report["method_registry"] = {k: METHODS[k] for k in m if k in METHODS}
    visual_root = Path(case_dir) if case_dir is not None else out
    try:
        visuals = generate_visual_artifacts(path, visual_root, m, reference_path=reference_path)
        if is_image and isinstance(m.get("autogan_spectral"), dict):
            autogan_visuals = generate_autogan_visual_artifacts(path, visual_root, m.get("autogan_spectral") or {})
            visuals = _merge_visual_artifacts(visuals, autogan_visuals)
        report["visual_artifacts"] = visuals
    except Exception as e:
        report["visual_artifacts"] = {
            "status": "error",
            "artifact_count": 0,
            "items": [],
            "errors": [{"id": "renderer", "error": repr(e)}],
            "warning": "Falha na renderização visual não invalida os resultados numéricos já registrados.",
        }
    write_json(out / (path.name + ".report.json"), report)
    return report


def analyze_case(case_dir: str | Path, profile: str = "full", run_veritas: bool = False) -> list[dict]:
    import yaml

    case = Path(case_dir)
    original = case / "original"
    results = case / "results"
    results.mkdir(parents=True, exist_ok=True)
    (case / "visuals").mkdir(parents=True, exist_ok=True)
    case_yaml = case / "case.yaml"
    reference_files = {}
    if case_yaml.exists():
        try:
            cfg = yaml.safe_load(case_yaml.read_text(encoding="utf-8")) or {}
            reference_files = (cfg.get("case") or {}).get("reference_files") or {}
        except Exception:
            reference_files = {}
    reports = []
    for p in sorted(original.glob("*")):
        if not p.is_file():
            continue
        ref_name = reference_files.get(p.name)
        ref_path = original / ref_name if ref_name else None
        if ref_path is not None and not ref_path.exists():
            ref_path = None
        try:
            reports.append(analyze_file(
                p, results, profile=profile, case_dir=case,
                run_veritas=run_veritas, reference_path=ref_path,
            ))
        except Exception as e:
            write_json(results / (p.name + ".error.json"), {"file": str(p), "error": repr(e)})
    write_json(case / "report.json", {
        "schema_version": "0.7",
        "case_id": case.name,
        "profile": profile,
        "veritas_crosscheck_requested": bool(run_veritas),
        "reference_files": reference_files,
        "reports": reports,
    })
    return reports
