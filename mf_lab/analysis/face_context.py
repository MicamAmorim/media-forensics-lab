from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from mf_lab.utils.io import cv_imread


def face_context_consistency(path: str | Path) -> dict:
    """Compare face-region texture/noise/sharpness with nearby non-face context.

    This is a screening aid for local face replacement. Lighting, makeup, depth
    of field and compression may create the same differences.
    """
    img = cv_imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"unreadable image: {path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(48, 48)) if not cascade.empty() else []
    rows = []
    H, W = gray.shape
    for x, y, w, h in faces[:10]:
        face = gray[y:y+h, x:x+w].astype(np.float32) / 255.0
        pad_x, pad_y = max(8, w // 3), max(8, h // 3)
        x0, y0 = max(0, x-pad_x), max(0, y-pad_y)
        x1, y1 = min(W, x+w+pad_x), min(H, y+h+pad_y)
        ctx = gray[y0:y1, x0:x1].astype(np.float32) / 255.0
        mask = np.ones(ctx.shape, dtype=bool)
        fx0, fy0 = x-x0, y-y0
        mask[fy0:fy0+h, fx0:fx0+w] = False
        bg = ctx[mask]
        if bg.size < 100:
            continue
        face_res = face - cv2.GaussianBlur(face, (0, 0), 1.0)
        ctx_blur = cv2.GaussianBlur(ctx, (0, 0), 1.0)
        bg_res = (ctx - ctx_blur)[mask]
        face_std = float(np.std(face_res))
        bg_std = float(np.std(bg_res))
        noise_ratio = face_std / (bg_std + 1e-12)
        face_lap = float(cv2.Laplacian(face, cv2.CV_32F).var())
        bg_img = np.zeros_like(ctx)
        bg_img[mask] = ctx[mask]
        bg_lap_values = cv2.Laplacian(bg_img, cv2.CV_32F)[mask]
        bg_lap = float(np.var(bg_lap_values)) if bg_lap_values.size else 0.0
        sharp_ratio = face_lap / (bg_lap + 1e-12)
        flags = []
        if noise_ratio < 0.45 or noise_ratio > 2.2:
            flags.append("face_context_noise_mismatch")
        if sharp_ratio < 0.35 or sharp_ratio > 2.8:
            flags.append("face_context_sharpness_mismatch")
        rows.append({
            "bbox": [int(x), int(y), int(w), int(h)],
            "face_residual_std": face_std,
            "context_residual_std": bg_std,
            "face_context_noise_ratio": float(noise_ratio),
            "face_context_sharpness_ratio": float(sharp_ratio),
            "screening_flags": flags,
        })
    flags = sorted({f for r in rows for f in r["screening_flags"]})
    return {
        "status": "screening_only",
        "faces_detected": int(len(faces)),
        "faces_analyzed": len(rows),
        "face_context_metrics": rows,
        "screening_flags": flags,
        "calibrated": False,
        "warning": "Face/context mismatch is non-specific and must not be treated as proof of face replacement or deepfake.",
    }
