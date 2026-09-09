from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
from mf_lab.utils.io import cv_imread


def score_synthetic_onnx(path: str | Path, model_path: str | Path | None = None) -> dict:
    """Optional ONNX deep detector adapter.

    The adapter is model-agnostic and disabled unless an ONNX model is explicitly
    configured. Expected input is NCHW RGB float32 in [0,1].
    """
    raw_model = str(model_path) if model_path is not None else os.environ.get("MFLAB_SYNTHETIC_ONNX", "")
    if not raw_model:
        return {
            "status": "not_configured",
            "validated": False,
            "warning": "Set MFLAB_SYNTHETIC_ONNX to enable an explicitly validated ONNX detector.",
        }
    model_path = Path(raw_model)
    if not model_path.is_file():
        return {"status": "error", "validated": False, "error": f"model_not_found: {model_path}"}
    try:
        import onnxruntime as ort
    except Exception as exc:
        return {"status": "runtime_unavailable", "validated": False, "error": repr(exc)}
    img = cv_imread(path, cv2.IMREAD_COLOR)
    if img is None:
        return {"status": "error", "validated": False, "error": "unreadable_image"}
    sess = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    shape = inp.shape
    h = int(shape[2]) if len(shape) == 4 and isinstance(shape[2], int) else 224
    w = int(shape[3]) if len(shape) == 4 and isinstance(shape[3], int) else 224
    rgb = cv2.cvtColor(cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x = np.transpose(rgb, (2, 0, 1))[None]
    out = np.asarray(sess.run(None, {inp.name: x})[0]).reshape(-1)
    if out.size == 1:
        score = float(1.0 / (1.0 + np.exp(-out[0])))
    else:
        z = out - out.max()
        p = np.exp(z) / np.exp(z).sum()
        score = float(p[-1])
    validated = os.environ.get("MFLAB_SYNTHETIC_ONNX_VALIDATED", "0") == "1"
    return {
        "status": "success",
        "model_name": model_path.stem,
        "score_synthetic": score,
        "validated": validated,
        "calibrated": False,
        "warning": "ONNX score is not a calibrated probability unless the supplied model documentation establishes calibration and domain validity.",
    }
