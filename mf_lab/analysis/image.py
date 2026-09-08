from __future__ import annotations
import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops
from scipy.fft import dctn


def ela(path: str | Path, quality: int = 90) -> dict:
    """Error Level Analysis. Screening aid only; never conclusive by itself."""
    im = Image.open(path).convert("RGB")
    b = io.BytesIO(); im.save(b, "JPEG", quality=quality); b.seek(0)
    rec = Image.open(b).convert("RGB")
    diff = ImageChops.difference(im, rec)
    arr = np.asarray(diff, dtype=np.float32)
    return {"mean_abs_error": float(arr.mean()), "max_error": int(arr.max()), "quality": quality,
            "warning": "ELA is exploratory only and is not proof of manipulation."}


def noise_residual_stats(path: str | Path) -> dict:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("unreadable image")
    imgf = img.astype(np.float32) / 255.0
    den = cv2.GaussianBlur(imgf, (0, 0), 1.0)
    r = imgf - den
    return {"mean": float(r.mean()), "std": float(r.std()), "mad": float(np.median(np.abs(r - np.median(r))))}


def jpeg_dct_periodicity(path: str | Path) -> dict:
    """Simple research/teaching heuristic for periodic gaps in DCT histograms.

    This remains a screening feature, not a calibrated double-JPEG detector.
    """
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("unreadable image")
    h, w = img.shape; h -= h % 8; w -= w % 8; img = img[:h, :w].astype(np.float32) - 128
    coeffs = []
    for y in range(0, h, 8):
        for x in range(0, w, 8):
            c = dctn(img[y:y + 8, x:x + 8], type=2, norm="ortho")
            coeffs.append(c[1, 2])
    q = np.rint(np.asarray(coeffs)).astype(int)
    if q.size < 10:
        return {"score": 0.0, "n_blocks": int(q.size)}
    lo, hi = np.percentile(q, [2, 98]).astype(int); bins = np.arange(lo, hi + 2)
    hist, _ = np.histogram(q, bins=bins)
    if len(hist) < 5:
        return {"score": 0.0, "n_blocks": int(q.size)}
    z = float(np.mean(hist == 0))
    alt = float(np.mean(np.abs(np.diff(hist)))) / (float(np.mean(hist)) + 1e-9)
    score = min(1.0, 0.5 * z + 0.05 * alt)
    return {
        "score": score,
        "n_blocks": int(q.size),
        "zero_bin_fraction": z,
        "status": "screening_only",
        "warning": "Heuristic indicator; cite/validate a published detector before evidentiary use.",
    }


def copy_move_orb(
    path: str | Path,
    descriptor_distance: int = 55,
    spatial_distance: float = 40.0,
    displacement_bin_px: float = 8.0,
    min_cluster_matches: int = 10,
    max_cluster_mean_hamming: float = 40.0,
    max_cluster_displacement_std: float = 1.2,
) -> dict:
    """ORB copy-move screening with self-match suppression and translation clustering.

    The previous implementation used ``crossCheck=True`` while matching the
    descriptor set against itself. In practice every descriptor preferred its
    identity match, leaving no usable non-self matches. This implementation
    explicitly requests several nearest neighbours, suppresses identity matches,
    and looks for a coherent repeated translation among low-Hamming matches.

    The thresholds are regression-tested on the controlled demo fixture only;
    they are not population-level forensic error rates.
    """
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("unreadable image")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=5000, fastThreshold=7)
    kp, des = orb.detectAndCompute(gray, None)
    if des is None or len(kp) < 4:
        return {
            "keypoints": len(kp),
            "candidate_pairs": 0,
            "suspicious_pairs": 0,
            "translation_clusters": [],
            "score": 0.0,
            "status": "screening_only",
        }

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    knn = matcher.knnMatch(des, des, k=min(5, len(des)))
    candidates = []
    seen_pairs: set[tuple[int, int]] = set()
    for query_idx, matches in enumerate(knn):
        for mt in matches:
            if mt.trainIdx == query_idx:
                continue
            pair_key = tuple(sorted((query_idx, mt.trainIdx)))
            if pair_key in seen_pairs:
                continue
            p1 = np.asarray(kp[query_idx].pt, dtype=np.float64)
            p2 = np.asarray(kp[mt.trainIdx].pt, dtype=np.float64)
            separation = float(np.linalg.norm(p1 - p2))
            if mt.distance <= descriptor_distance and separation >= spatial_distance:
                seen_pairs.add(pair_key)
                displacement = p2 - p1
                if displacement[0] < 0 or (abs(displacement[0]) < 1e-12 and displacement[1] < 0):
                    p1, p2 = p2, p1
                    displacement = -displacement
                candidates.append({
                    "query_idx": int(query_idx),
                    "train_idx": int(mt.trainIdx),
                    "hamming": float(mt.distance),
                    "separation": separation,
                    "p1": p1,
                    "p2": p2,
                    "displacement": displacement,
                })
                break

    bins: dict[tuple[int, int], list[dict]] = {}
    for row in candidates:
        dx, dy = row["displacement"]
        key = (int(round(dx / displacement_bin_px)), int(round(dy / displacement_bin_px)))
        bins.setdefault(key, []).append(row)

    clusters = []
    for rows in bins.values():
        d = np.asarray([r["displacement"] for r in rows], dtype=np.float64)
        p1 = np.asarray([r["p1"] for r in rows], dtype=np.float64)
        p2 = np.asarray([r["p2"] for r in rows], dtype=np.float64)
        mean_hamming = float(np.mean([r["hamming"] for r in rows]))
        disp_mean = d.mean(axis=0)
        disp_std_xy = d.std(axis=0)
        disp_std = float(np.linalg.norm(disp_std_xy))
        suspicious = (
            len(rows) >= min_cluster_matches
            and mean_hamming <= max_cluster_mean_hamming
            and disp_std <= max_cluster_displacement_std
        )
        clusters.append({
            "matches": len(rows),
            "mean_hamming": mean_hamming,
            "translation_px": [float(disp_mean[0]), float(disp_mean[1])],
            "translation_std_px": [float(disp_std_xy[0]), float(disp_std_xy[1])],
            "translation_std_norm": disp_std,
            "source_bbox": [
                float(p1[:, 0].min()), float(p1[:, 1].min()),
                float(p1[:, 0].max()), float(p1[:, 1].max()),
            ],
            "destination_bbox": [
                float(p2[:, 0].min()), float(p2[:, 1].min()),
                float(p2[:, 0].max()), float(p2[:, 1].max()),
            ],
            "suspicious": bool(suspicious),
        })

    clusters.sort(key=lambda c: (c["suspicious"], c["matches"], -c["mean_hamming"]), reverse=True)
    suspicious_clusters = [c for c in clusters if c["suspicious"]]
    suspicious_pairs = int(sum(c["matches"] for c in suspicious_clusters))
    score = min(1.0, suspicious_pairs / 20.0)
    dominant = suspicious_clusters[0] if suspicious_clusters else None
    return {
        "keypoints": len(kp),
        "candidate_pairs": len(candidates),
        "suspicious_pairs": suspicious_pairs,
        "suspicious_cluster_count": len(suspicious_clusters),
        "dominant_translation_px": dominant["translation_px"] if dominant else None,
        "translation_clusters": clusters[:25],
        "score": score,
        "status": "screening_only",
        "thresholds": {
            "descriptor_distance": descriptor_distance,
            "spatial_distance": spatial_distance,
            "displacement_bin_px": displacement_bin_px,
            "min_cluster_matches": min_cluster_matches,
            "max_cluster_mean_hamming": max_cluster_mean_hamming,
            "max_cluster_displacement_std": max_cluster_displacement_std,
        },
        "warning": "Feature matching is a screening detector; repetitive textures and near-duplicate scene structures can cause false positives. Confirm localization manually or with a validated copy-move method.",
    }
