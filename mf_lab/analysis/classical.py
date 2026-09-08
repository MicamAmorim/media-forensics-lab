from __future__ import annotations

import io
import math
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
from PIL import Image
from scipy import stats
from scipy.fft import fft2, fftshift


def _read_bgr(path: str | Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"unreadable image: {path}")
    return img


def histogram_analysis(path: str | Path) -> dict:
    """Descriptive RGB histogram analysis.

    This does not classify an image as authentic/fake. It exposes clipping,
    channel imbalance, entropy, and unusually sparse histograms that can be
    useful when interpreted together with the editing history and image type.
    """
    bgr = _read_bgr(path)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    result: dict = {"channels": {}, "warning": "Histogram anomalies are non-specific and require contextual interpretation."}
    for idx, name in enumerate(("R", "G", "B")):
        ch = rgb[:, :, idx]
        hist = cv2.calcHist([ch], [0], None, [256], [0, 256]).ravel().astype(np.float64)
        p = hist / max(hist.sum(), 1.0)
        nz = p[p > 0]
        entropy = float(-(nz * np.log2(nz)).sum())
        result["channels"][name] = {
            "mean": float(ch.mean()),
            "std": float(ch.std()),
            "entropy_bits": entropy,
            "zero_bins": int(np.count_nonzero(hist == 0)),
            "clipped_black_fraction": float(np.mean(ch == 0)),
            "clipped_white_fraction": float(np.mean(ch == 255)),
        }
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    result["gray_dynamic_range"] = int(gray.max()) - int(gray.min())
    return result


def noise_map_analysis(path: str | Path, block_size: int = 64) -> dict:
    """High-pass residual consistency screening."""
    gray = cv2.cvtColor(_read_bgr(path), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    den = cv2.GaussianBlur(gray, (0, 0), 1.2)
    residual = gray - den
    h, w = residual.shape
    local = []
    for y in range(0, h - block_size + 1, block_size):
        for x in range(0, w - block_size + 1, block_size):
            block = residual[y:y + block_size, x:x + block_size]
            local.append(float(np.std(block)))
    mean_local = float(np.mean(local)) if local else float(np.std(residual))
    cv_local = float(np.std(local) / (mean_local + 1e-12)) if local else 0.0
    return {
        "residual_mean": float(residual.mean()),
        "residual_std": float(residual.std()),
        "residual_mad": float(np.median(np.abs(residual - np.median(residual)))),
        "block_size": block_size,
        "blocks": len(local),
        "local_std_mean": mean_local,
        "local_std_cv": cv_local,
        "warning": "Noise residual inconsistency is a screening clue; scene texture, denoising, HDR and recompression can create similar patterns.",
    }


def jpeg_ghost_analysis(path: str | Path, qualities: Iterable[int] = range(55, 101, 5)) -> dict:
    """Multi-quality JPEG ghost screening."""
    with Image.open(path) as im0:
        im = im0.convert("RGB")
        orig = np.asarray(im, dtype=np.float32)
        rows = []
        for q in qualities:
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=int(q))
            buf.seek(0)
            rec = np.asarray(Image.open(buf).convert("RGB"), dtype=np.float32)
            diff = np.mean(np.abs(orig - rec), axis=2)
            local = []
            h, w = diff.shape
            for y in range(0, h - 31, 32):
                for x in range(0, w - 31, 32):
                    local.append(float(diff[y:y + 32, x:x + 32].mean()))
            rows.append({
                "quality": int(q),
                "mean_abs_error": float(diff.mean()),
                "local_cv": float(np.std(local) / (np.mean(local) + 1e-12)) if local else 0.0,
            })
    best = min(rows, key=lambda r: r["mean_abs_error"]) if rows else None
    return {
        "quality_sweep": rows,
        "minimum_error_quality": best["quality"] if best else None,
        "minimum_mean_abs_error": best["mean_abs_error"] if best else None,
        "warning": "JPEG ghost analysis is exploratory; prior recompression may be benign and social-media pipelines can dominate the signal.",
    }


def jpeg_quantization_analysis(path: str | Path) -> dict:
    with Image.open(path) as im:
        if (im.format or "").upper() != "JPEG":
            return {"available": False, "reason": "not_jpeg"}
        qtables = getattr(im, "quantization", None) or {}
    tables = {str(k): [int(v) for v in vals] for k, vals in qtables.items()}
    fingerprints = {}
    for key, vals in tables.items():
        arr = np.asarray(vals, dtype=np.int32)
        fingerprints[key] = {
            "sum": int(arr.sum()),
            "mean": float(arr.mean()),
            "min": int(arr.min()) if arr.size else None,
            "max": int(arr.max()) if arr.size else None,
            "first_16": arr[:16].tolist(),
        }
    return {"available": bool(tables), "table_count": len(tables), "tables": tables, "fingerprints": fingerprints,
            "warning": "Quantization tables can indicate encoding history/software families but are not unique identifiers of manipulation."}


def frequency_analysis(path: str | Path, radial_bins: int = 64) -> dict:
    gray = cv2.cvtColor(_read_bgr(path), cv2.COLOR_BGR2GRAY).astype(np.float32)
    gray -= float(gray.mean())
    mag = np.log1p(np.abs(fftshift(fft2(gray))))
    h, w = mag.shape
    cy, cx = h // 2, w // 2
    yy, xx = np.ogrid[:h, :w]
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    max_r = max(1.0, min(cy, cx))
    profile = []
    for i in range(radial_bins):
        r0 = i * max_r / radial_bins
        r1 = (i + 1) * max_r / radial_bins
        m = (rr >= r0) & (rr < r1)
        profile.append(float(mag[m].mean()) if np.any(m) else 0.0)
    p = np.asarray(profile, dtype=np.float64)
    low = float(p[1:max(2, radial_bins // 4)].mean())
    high = float(p[max(2, radial_bins * 3 // 4):].mean())
    high_low_ratio = float(high / (low + 1e-12))
    z = (p - p.mean()) / (p.std() + 1e-12)
    peak_idx = [i for i in range(1, len(z) - 1) if z[i] > 1.5 and z[i] > z[i - 1] and z[i] > z[i + 1]]
    rmask = rr > max_r * 0.08
    quadrants = [mag[:cy, :cx][rmask[:cy, :cx]], mag[:cy, cx:][rmask[:cy, cx:]], mag[cy:, :cx][rmask[cy:, :cx]], mag[cy:, cx:][rmask[cy:, cx:]]]
    qmeans = [float(q.mean()) if q.size else 0.0 for q in quadrants]
    qcv = float(np.std(qmeans) / (np.mean(qmeans) + 1e-12))
    return {"radial_profile": profile, "high_low_frequency_ratio": high_low_ratio, "spectral_peak_indices": peak_idx,
            "spectral_peak_count": len(peak_idx), "quadrant_mean_cv": qcv,
            "warning": "Frequency-domain patterns are model- and processing-dependent; use only as one evidence family."}


def resampling_analysis(path: str | Path, max_lag: int = 32) -> dict:
    """Second-derivative autocorrelation screening for interpolation traces.

    The raw lag-1 autocorrelation is naturally high for many photographs and
    was previously treated as if it were discriminative. We now expose both
    the raw autocorrelation and a short-lag persistence ratio (lag2/lag1).
    """
    gray = cv2.cvtColor(_read_bgr(path), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    d2x = np.abs(cv2.Sobel(gray, cv2.CV_32F, 2, 0, ksize=3)).mean(axis=0)
    d2y = np.abs(cv2.Sobel(gray, cv2.CV_32F, 0, 2, ksize=3)).mean(axis=1)
    def ac(v: np.ndarray) -> list[float]:
        v = np.asarray(v, dtype=np.float64); v -= v.mean(); denom = float(np.dot(v, v)) + 1e-12
        return [float(np.dot(v[:-lag], v[lag:]) / denom) for lag in range(1, min(max_lag, len(v) - 1) + 1)]
    ax, ay = ac(d2x), ac(d2y)
    max_x = max(ax) if ax else 0.0; max_y = max(ay) if ay else 0.0
    def lag_persistence(a: list[float]) -> float | None:
        if len(a) < 2 or abs(a[0]) < 1e-12: return None
        return float(a[1] / a[0])
    px, py = lag_persistence(ax), lag_persistence(ay)
    vals = [v for v in (px, py) if v is not None]
    persistence = max(vals) if vals else None
    flag = bool(persistence is not None and persistence >= 0.94)
    return {"x_autocorrelation": ax, "y_autocorrelation": ay, "max_nonzero_autocorrelation": float(max(max_x, max_y)),
            "short_lag_persistence_x": px, "short_lag_persistence_y": py, "short_lag_persistence": persistence,
            "screening_flag": flag, "screening_threshold": 0.94, "status": "screening_only",
            "warning": "This is a resampling screening heuristic, not a calibrated detector. Confirm with a published/validated method before evidentiary use."}


def lsb_steganography_screen(path: str | Path) -> dict:
    rgb = cv2.cvtColor(_read_bgr(path), cv2.COLOR_BGR2RGB)
    channels = {}
    for idx, name in enumerate(("R", "G", "B")):
        bits = (rgb[:, :, idx].ravel() & 1).astype(np.int8)
        n0 = int(np.count_nonzero(bits == 0)); n1 = int(bits.size - n0); total = max(1, bits.size); p1 = n1 / total
        entropy = 0.0
        for p in (p1, 1.0 - p1):
            if p > 0: entropy -= p * math.log2(p)
        expected = total / 2.0; chi2 = ((n0 - expected) ** 2 + (n1 - expected) ** 2) / (expected + 1e-12)
        channels[name] = {"n0": n0, "n1": n1, "p1": float(p1), "entropy_bits": float(entropy), "chi2": float(chi2), "pvalue": float(stats.chi2.sf(chi2, df=1))}
    return {"channels": channels, "warning": "Balanced LSBs are not proof of steganography; modern embedding and natural image statistics require specialized steganalysis."}


def perceptual_hashes(path: str | Path) -> dict:
    gray = cv2.cvtColor(_read_bgr(path), cv2.COLOR_BGR2GRAY)
    def bits_to_hex(bits: np.ndarray) -> str:
        bits = np.asarray(bits, dtype=np.uint8).ravel(); pad = (-len(bits)) % 4
        if pad: bits = np.pad(bits, (0, pad))
        out = ""
        for i in range(0, len(bits), 4):
            out += format(int(bits[i] * 8 + bits[i + 1] * 4 + bits[i + 2] * 2 + bits[i + 3]), "x")
        return out
    a = cv2.resize(gray, (8, 8), interpolation=cv2.INTER_AREA); ahash = bits_to_hex(a >= a.mean())
    d = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA); dhash = bits_to_hex(d[:, 1:] >= d[:, :-1])
    p = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32); c = cv2.dct(p)[:8, :8]; med = np.median(c[1:, :]); phash = bits_to_hex(c >= med)
    return {"ahash": ahash, "dhash": dhash, "phash": phash, "note": "Perceptual hashes are for similarity/provenance triage, not file integrity."}


def extract_prnu_residual(path: str | Path) -> np.ndarray:
    bgr = _read_bgr(path).astype(np.float32) / 255.0
    residuals = []
    for c in range(3):
        ch = bgr[:, :, c]; den = cv2.GaussianBlur(ch, (0, 0), 1.0); residuals.append(ch - den)
    return np.stack(residuals, axis=2)


def prnu_screen(path: str | Path, block_size: int = 64) -> dict:
    r = extract_prnu_residual(path); h, w = r.shape[:2]; energies = []
    for y in range(0, h - block_size + 1, block_size):
        for x in range(0, w - block_size + 1, block_size):
            energies.append(float(np.std(r[y:y + block_size, x:x + block_size])))
    mean_e = float(np.mean(energies)) if energies else float(np.std(r)); cv_e = float(np.std(energies) / (mean_e + 1e-12)) if energies else 0.0
    return {"residual_std": float(r.std()), "local_energy_mean": mean_e, "local_energy_cv": cv_e, "blocks": len(energies), "status": "screening_only",
            "warning": "This is not source-camera identification. A forensic PRNU comparison should build a fingerprint from multiple known images and use a calibrated correlation/PCE procedure."}
