from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

from mf_lab.analysis.autogan_spectral import AUTOGAN_MODES, autogan_spectral_tensor


ENV_CHECKPOINT = "MFLAB_AUTOGAN_CHECKPOINT"
ENV_METADATA = "MFLAB_AUTOGAN_METADATA"
ENV_MODE = "MFLAB_AUTOGAN_FEATURE_MODE"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _metadata_path(checkpoint: Path) -> Path | None:
    raw = os.environ.get(ENV_METADATA, "").strip()
    if raw:
        return Path(raw)
    candidates = [
        checkpoint.with_suffix(checkpoint.suffix + ".json"),
        checkpoint.with_suffix(".json"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _load_metadata(checkpoint: Path) -> dict:
    path = _metadata_path(checkpoint)
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def status() -> dict:
    raw = os.environ.get(ENV_CHECKPOINT, "").strip()
    configured = bool(raw)
    path = Path(raw) if raw else None
    mode = os.environ.get(ENV_MODE, "full").strip().lower() or "full"
    return {
        "configured": configured,
        "checkpoint": str(path) if path else None,
        "checkpoint_exists": bool(path and path.is_file()),
        "feature_mode": mode,
        "supported_modes": sorted(AUTOGAN_MODES),
        "runtime": "optional_torch_torchvision",
        "scope": "GAN upsampling spectral detector compatibility adapter",
    }


def _normalize_state_dict(state: dict) -> dict:
    cleaned = {}
    for key, value in state.items():
        name = str(key)
        if name.startswith("module."):
            name = name[len("module."):]
        cleaned[name] = value
    return cleaned


@lru_cache(maxsize=4)
def _load_runtime(checkpoint_str: str, checkpoint_mtime_ns: int):
    # Import lazily so the core MFLab installation remains free of heavy Torch
    # dependencies unless the user explicitly enables this integration.
    import torch
    import torch.nn as nn
    from torchvision import models

    checkpoint = Path(checkpoint_str)
    model = models.resnet34(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 2)
    payload = torch.load(checkpoint, map_location="cpu")
    if isinstance(payload, dict) and isinstance(payload.get("state_dict"), dict):
        state = payload["state_dict"]
    elif isinstance(payload, dict):
        state = payload
    else:
        raise ValueError("unsupported AutoGAN checkpoint payload")
    model.load_state_dict(_normalize_state_dict(state), strict=True)
    model.eval()
    return torch, model


def score_autogan_checkpoint(path: str | Path) -> dict:
    """Score one image with an optional AutoGAN-compatible ResNet34 checkpoint.

    The original AutoGAN training data uses label 0 for fake and label 1 for
    real. Therefore `score_synthetic` is softmax class 0. The value is a model
    score; it is not called a calibrated probability unless explicit metadata
    supplied by the examiner documents calibration.
    """
    raw = os.environ.get(ENV_CHECKPOINT, "").strip()
    mode = os.environ.get(ENV_MODE, "full").strip().lower() or "full"
    if mode not in AUTOGAN_MODES:
        return {
            "status": "error",
            "reason": f"unsupported feature mode: {mode}",
            "validated": False,
            "calibrated": False,
        }
    if not raw:
        return {
            "status": "not_configured",
            "reason": f"set {ENV_CHECKPOINT} to enable the optional AutoGAN-compatible checkpoint adapter",
            "model_name": "autogan_resnet34_spectral_compatible",
            "validated": False,
            "calibrated": False,
            "screening_only": True,
        }

    checkpoint = Path(raw)
    if not checkpoint.is_file():
        return {
            "status": "unavailable",
            "reason": f"checkpoint not found: {checkpoint}",
            "model_name": "autogan_resnet34_spectral_compatible",
            "validated": False,
            "calibrated": False,
            "screening_only": True,
        }

    try:
        torch, model = _load_runtime(str(checkpoint.resolve()), checkpoint.stat().st_mtime_ns)
    except ImportError as exc:
        return {
            "status": "unavailable",
            "reason": f"optional torch/torchvision runtime unavailable: {exc}",
            "model_name": "autogan_resnet34_spectral_compatible",
            "validated": False,
            "calibrated": False,
            "screening_only": True,
        }
    except Exception as exc:
        return {
            "status": "error",
            "reason": repr(exc),
            "model_name": "autogan_resnet34_spectral_compatible",
            "validated": False,
            "calibrated": False,
            "screening_only": True,
        }

    tensor = autogan_spectral_tensor(path, mode=mode)
    x = torch.from_numpy(np.ascontiguousarray(tensor[None, ...])).float()
    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

    score_synthetic = float(probs[0])
    score_real = float(probs[1])
    metadata = _load_metadata(checkpoint)
    validated = bool(metadata.get("validated", False))
    calibrated = bool(metadata.get("calibrated", False))
    validation = metadata.get("validation") if isinstance(metadata.get("validation"), dict) else None

    return {
        "status": "success",
        "model_name": str(metadata.get("model_name") or "autogan_resnet34_spectral_compatible"),
        "architecture": "resnet34",
        "feature": "fft",
        "feature_mode": mode,
        "label_convention": {"0": "synthetic", "1": "real"},
        "score_synthetic": score_synthetic,
        "score_real": score_real,
        "score": score_synthetic,
        "predicted_label": "synthetic" if score_synthetic >= score_real else "real",
        "checkpoint_sha256": _sha256(checkpoint),
        "validated": validated,
        "calibrated": calibrated,
        "validation": validation,
        "screening_only": not validated,
        "source_method": "Zhang, Karaman and Chang, WIFS 2019",
        "method_scope": "GAN upsampling spectral detector; a negative score does not exclude diffusion or other non-GAN synthetic media.",
        "warning": (
            "The detector score is not a posterior probability unless calibration is explicitly documented. "
            "Unvalidated checkpoints remain screening observations only."
        ),
    }
