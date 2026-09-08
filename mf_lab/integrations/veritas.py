from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Callable

# CodeRafay/Forensic-Image-Analysis-Toolkit ("Veritas") is BSD-3-Clause.
# We intentionally do not vendor its source here.  When a local checkout is
# available this adapter can execute the upstream implementation as a SECONDARY
# comparison. MFLab native methods remain the primary reproducible pipeline.
FEATURES: dict[str, tuple[str, str]] = {
    "ela": ("ela.py", "perform_ela"),
    "metadata": ("metadata_analysis.py", "extract_metadata"),
    "histogram": ("histogram_analysis.py", "generate_histogram"),
    "noise_map": ("noise_map.py", "generate_noise_map"),
    "jpeg_ghost": ("jpeg_ghost.py", "detect_jpeg_ghost"),
    "quantization": ("quant_table.py", "analyze_quantization_table"),
    "copy_move": ("cmfd.py", "detect_copy_move"),
    "prnu": ("prnu.py", "analyze_prnu"),
    "frequency": ("frequency_analysis.py", "analyze_frequency_domain"),
    "deepfake": ("deepfake_detector.py", "detect_deepfake_artifacts"),
    "gan_fingerprint": ("deepfake_detector.py", "detect_gan_fingerprint"),
    "resampling": ("resampling_detector.py", "detect_resampling"),
    "steganography": ("steganography_detection.py", "detect_lsb_steganography"),
    "hash_verification": ("hash_verification.py", "verify_image_provenance"),
}

# The current upstream deepfake_artifacts function contains a use-after-delete
# bug (img_array is deleted before img_array.shape is read).  We expose it only
# when explicitly requested and record the error instead of silently treating it
# as a detector verdict.
KNOWN_UPSTREAM_ISSUES = {
    "deepfake": "Current upstream implementation is a simplified heuristic and contains a use-after-delete bug in detect_deepfake_artifacts; never use its output as a forensic conclusion.",
    "prnu": "Upstream implementation is a single-image Gaussian residual heuristic, not a calibrated multi-reference camera fingerprint/PCE procedure.",
    "hash_verification": "Upstream 'blockchain' wording refers to a local JSON provenance database, not a cryptographic blockchain network.",
}


def default_toolkit_path() -> Path:
    env = os.environ.get("VERITAS_TOOLKIT_PATH")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / ".external" / "Forensic-Image-Analysis-Toolkit"


def status(toolkit_path: str | Path | None = None) -> dict:
    root = Path(toolkit_path) if toolkit_path else default_toolkit_path()
    analysis = root / "analysis"
    available: dict[str, bool] = {}
    for feature, (module_file, _) in FEATURES.items():
        available[feature] = (analysis / module_file).exists()
    return {
        "toolkit": "CodeRafay/Forensic-Image-Analysis-Toolkit (Veritas)",
        "path": str(root),
        "installed": analysis.is_dir(),
        "features": available,
        "license": "BSD-3-Clause",
        "mode": "optional_secondary_implementation",
        "known_upstream_issues": KNOWN_UPSTREAM_ISSUES,
    }


def _load_function(module_path: Path, fn_name: str) -> Callable:
    spec = importlib.util.spec_from_file_location(f"mflab_ext_{module_path.stem}", module_path)
    if not spec or not spec.loader:
        raise ImportError(f"cannot load {module_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, fn_name, None)
    if not callable(fn):
        raise AttributeError(f"{fn_name} not found in {module_path}")
    return fn


def _json_safe(value: Any) -> Any:
    """Best-effort conversion of third-party results into report-safe JSON."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    # numpy scalars/arrays and PIL objects without importing those packages here.
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            pass
    if hasattr(value, "tolist"):
        try:
            return _json_safe(value.tolist())
        except Exception:
            pass
    return repr(value)


def run_feature(feature: str, image_path: str | Path, toolkit_path: str | Path | None = None, **kwargs) -> dict:
    """Run one upstream Veritas feature if a local checkout is available.

    This is deliberately opt-in. Executing arbitrary third-party code during a
    forensic case should be recorded, version-pinned and validated before it is
    relied upon. Results are therefore tagged as a secondary cross-check.
    """
    if feature not in FEATURES:
        return {"status": "unsupported", "feature": feature}
    root = Path(toolkit_path) if toolkit_path else default_toolkit_path()
    module_file, fn_name = FEATURES[feature]
    module_path = root / "analysis" / module_file
    if not module_path.exists():
        return {
            "status": "unavailable",
            "feature": feature,
            "reason": "upstream_checkout_not_found",
            "expected": str(module_path),
        }
    try:
        fn = _load_function(module_path, fn_name)
        result = fn(str(image_path), **kwargs)
        return {
            "status": "success",
            "feature": feature,
            "implementation": "CodeRafay/Forensic-Image-Analysis-Toolkit",
            "function": fn_name,
            "secondary_only": True,
            "known_issue": KNOWN_UPSTREAM_ISSUES.get(feature),
            "upstream_result": _json_safe(result),
        }
    except Exception as e:
        return {
            "status": "error",
            "feature": feature,
            "implementation": "CodeRafay/Forensic-Image-Analysis-Toolkit",
            "function": fn_name,
            "secondary_only": True,
            "known_issue": KNOWN_UPSTREAM_ISSUES.get(feature),
            "error": repr(e),
        }


def run_all(image_path: str | Path, toolkit_path: str | Path | None = None) -> dict:
    """Run every image-oriented upstream feature as an explicit cross-check."""
    st = status(toolkit_path)
    if not st["installed"]:
        return {"status": "unavailable", "integration": st, "results": {}}
    results = {name: run_feature(name, image_path, toolkit_path) for name in FEATURES}
    return {
        "status": "complete",
        "integration": st,
        "results": results,
        "warning": "Upstream outputs are secondary screening evidence. MFLab does not adopt upstream authenticity scores or thresholds as forensic truth.",
    }
