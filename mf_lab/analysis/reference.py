from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from mf_lab.utils.io import cv_imread


def _read_bgr(path: str | Path) -> np.ndarray:
    p = Path(path)
    img = cv_imread(p, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"unreadable image: {p}")
    return img


def reference_image_difference(questioned: str | Path, reference: str | Path,
                               min_threshold: float = 12.0,
                               robust_sigma: float = 8.0,
                               min_component_area: int = 50) -> dict:
    """Reference-assisted localization of changed image regions.

    This compares a questioned image with a known reference of the same scene.
    It is useful for controlled validation and cases where a trustworthy source
    image is actually available. It is *not* a blind splice/inpainting detector.
    """
    q = _read_bgr(questioned)
    r = _read_bgr(reference)
    if q.shape != r.shape:
        return {
            "status": "not_comparable",
            "reason": "dimension_mismatch",
            "questioned_shape": list(q.shape),
            "reference_shape": list(r.shape),
            "reference_assisted": True,
        }

    diff = np.mean(np.abs(q.astype(np.float32) - r.astype(np.float32)), axis=2)
    med = float(np.median(diff))
    mad = float(np.median(np.abs(diff - med)))
    threshold = max(float(min_threshold), med + float(robust_sigma) * 1.4826 * mad)
    mask = (diff >= threshold).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))

    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    comps = []
    for i in range(1, n):
        x, y, w, h, area = [int(v) for v in stats[i]]
        if area < min_component_area:
            continue
        vals = diff[labels == i]
        comps.append({
            "bbox_xywh": [x, y, w, h],
            "area_px": area,
            "mean_abs_difference": float(vals.mean()) if vals.size else None,
        })
    comps.sort(key=lambda c: c["area_px"], reverse=True)
    largest = comps[0] if comps else None
    return {
        "status": "success",
        "reference_assisted": True,
        "reference": str(reference),
        "median_abs_difference": med,
        "robust_mad": mad,
        "threshold": float(threshold),
        "changed_fraction": float(np.mean(mask > 0)),
        "component_count": len(comps),
        "components": comps[:20],
        "largest_component_bbox_xywh": largest["bbox_xywh"] if largest else None,
        "warning": (
            "Reference-assisted localization only. It requires a trustworthy, scene-compatible reference and "
            "does not by itself identify whether the change is splice, inpainting, face replacement or another edit."
        ),
    }


def _video_frames(path: str | Path, size: tuple[int, int] = (64, 64)) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), size, interpolation=cv2.INTER_AREA)
        frames.append(gray.astype(np.float32))
    cap.release()
    if not frames:
        return np.empty((0, size[1], size[0]), dtype=np.float32)
    return np.stack(frames)


def reference_video_sequence_alignment(questioned: str | Path, reference: str | Path) -> dict:
    """Reference-assisted monotonic frame alignment for deletion/skip detection."""
    q = _video_frames(questioned)
    r = _video_frames(reference)
    if len(q) == 0 or len(r) == 0:
        return {"status": "error", "reason": "could_not_decode_video", "reference_assisted": True}
    if len(q) > len(r):
        return {
            "status": "not_comparable",
            "reason": "questioned_longer_than_reference",
            "questioned_frames": int(len(q)),
            "reference_frames": int(len(r)),
            "reference_assisted": True,
        }

    # Small demo/forensic clips: brute-force frame MAD is transparent and auditable.
    d = np.mean(np.abs(q[:, None, :, :] - r[None, :, :, :]), axis=(2, 3))
    matches = []
    last = -1
    for i in range(len(q)):
        candidates = np.arange(last + 1, len(r))
        if candidates.size == 0:
            break
        j = int(candidates[np.argmin(d[i, candidates])])
        matches.append(j)
        last = j

    skips = []
    for qi in range(1, len(matches)):
        prev_ref, next_ref = matches[qi - 1], matches[qi]
        if next_ref - prev_ref > 1:
            skips.append({
                "questioned_transition_index": int(qi),
                "previous_reference_index": int(prev_ref),
                "next_reference_index": int(next_ref),
                "skipped_reference_start": int(prev_ref + 1),
                "skipped_reference_end": int(next_ref - 1),
                "skipped_reference_count": int(next_ref - prev_ref - 1),
                "match_mad": float(d[qi, next_ref]),
            })
    return {
        "status": "success",
        "reference_assisted": True,
        "reference": str(reference),
        "questioned_frames": int(len(q)),
        "reference_frames": int(len(r)),
        "matched_reference_indices": [int(x) for x in matches],
        "skipped_segments": skips,
        "skip_count": len(skips),
        "warning": (
            "Reference-assisted sequence alignment requires a trustworthy corresponding reference video. "
            "It is not a blind detector of deleted segments."
        ),
    }
