from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from skimage.feature import graycomatrix, graycoprops, hog, local_binary_pattern

from mf_lab.analysis.classical import frequency_analysis, noise_map_analysis, prnu_screen, resampling_analysis
from mf_lab.utils.io import cv_imread

SCHEMA = "MFLAB-SYNTH-FEATURES-1.0"


def _read_rgb(path: str | Path) -> np.ndarray:
    bgr = cv_imread(path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"unreadable image: {path}")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def _finite(value: float | int | None) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return 0.0
    return x if np.isfinite(x) else 0.0


def _haar_energies(gray: np.ndarray, levels: int = 3) -> dict[str, float]:
    """Small dependency-free 2-D Haar pyramid.

    The coefficients are descriptive multiscale texture/frequency features; the
    transform is not itself a synthetic-image detector.
    """
    x = gray.astype(np.float32) / 255.0
    out: dict[str, float] = {}
    for level in range(1, levels + 1):
        h, w = x.shape
        h -= h % 2
        w -= w % 2
        if h < 4 or w < 4:
            break
        x = x[:h, :w]
        a, b = x[0::2, 0::2], x[0::2, 1::2]
        c, d = x[1::2, 0::2], x[1::2, 1::2]
        ll = (a + b + c + d) * 0.5
        lh = (a - b + c - d) * 0.5
        hl = (a + b - c - d) * 0.5
        hh = (a - b - c + d) * 0.5
        e_lh = float(np.mean(lh * lh))
        e_hl = float(np.mean(hl * hl))
        e_hh = float(np.mean(hh * hh))
        out[f"wavelet_l{level}_lh_energy"] = e_lh
        out[f"wavelet_l{level}_hl_energy"] = e_hl
        out[f"wavelet_l{level}_hh_energy"] = e_hh
        out[f"wavelet_l{level}_detail_energy"] = e_lh + e_hl + e_hh
        out[f"wavelet_l{level}_hf_total"] = e_lh + e_hl + e_hh
        x = ll
    return out


def _rgb_features(rgb: np.ndarray) -> dict[str, float]:
    flat = rgb.reshape(-1, 3).astype(np.float64)
    out: dict[str, float] = {}
    for a, b, name in ((0, 1, "rg"), (0, 2, "rb"), (1, 2, "gb")):
        xa, xb = flat[:, a], flat[:, b]
        if xa.std() * xb.std() > 1e-12:
            out[f"rgb_corr_{name}"] = _finite(np.corrcoef(xa, xb)[0, 1])
        else:
            out[f"rgb_corr_{name}"] = 0.0
    for idx, name in enumerate(("r", "g", "b")):
        ch = flat[:, idx]
        mu, sd = float(ch.mean()), float(ch.std())
        out[f"rgb_{name}_mean"] = mu
        out[f"rgb_{name}_std"] = sd
        out[f"rgb_{name}_skew"] = _finite(np.mean(((ch - mu) / (sd + 1e-12)) ** 3))
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    out["hsv_saturation_mean"] = float(hsv[:, :, 1].mean() / 255.0)
    out["hsv_saturation_std"] = float(hsv[:, :, 1].std() / 255.0)
    return out


def _texture_features(gray: np.ndarray) -> dict[str, float]:
    small = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA)
    quant = np.clip((small.astype(np.float32) / 256.0 * 16).astype(np.uint8), 0, 15)
    glcm = graycomatrix(quant, distances=[1, 2], angles=[0, np.pi / 4, np.pi / 2], levels=16, symmetric=True, normed=True)
    out: dict[str, float] = {}
    for prop in ("contrast", "dissimilarity", "homogeneity", "energy", "correlation"):
        out[f"texture_glcm_{prop}"] = _finite(np.mean(graycoprops(glcm, prop)))
    lbp = local_binary_pattern(small, P=8, R=1, method="uniform")
    hist, _ = np.histogram(lbp, bins=np.arange(0, 11), range=(0, 10), density=True)
    for i, v in enumerate(hist[:10]):
        out[f"texture_lbp_uniform_{i}"] = _finite(v)
    return out


def _hog_features(gray: np.ndarray) -> dict[str, float]:
    small = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA)
    vec = hog(small, orientations=9, pixels_per_cell=(16, 16), cells_per_block=(2, 2), block_norm="L2-Hys", feature_vector=True)
    return {
        "hog_mean": _finite(np.mean(vec)),
        "hog_std": _finite(np.std(vec)),
        "hog_p90": _finite(np.percentile(vec, 90)),
        "hog_sparsity": _finite(np.mean(vec < 1e-3)),
    }


def _fft_features(gray: np.ndarray) -> dict[str, float]:
    f = np.fft.fftshift(np.fft.fft2(gray.astype(np.float32) - float(gray.mean())))
    mag = np.log1p(np.abs(f))
    h, w = mag.shape
    cy, cx = h // 2, w // 2
    yy, xx = np.ogrid[:h, :w]
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    rmax = max(1.0, min(cy, cx))
    bands = []
    for lo, hi in ((0.05, 0.25), (0.25, 0.50), (0.50, 0.75), (0.75, 1.0)):
        mask = (rr >= lo * rmax) & (rr < hi * rmax)
        bands.append(float(mag[mask].mean()) if np.any(mask) else 0.0)
    out = {f"fft_band_{i}_mean": _finite(v) for i, v in enumerate(bands, 1)}
    out["fft_hf_lf_ratio"] = _finite(bands[-1] / (bands[0] + 1e-12))
    return out


def synthetic_feature_bank(path: str | Path) -> dict:
    """Explainable feature bank for research on synthetic/deepfake imagery."""
    rgb = _read_rgb(path)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    features: dict[str, float] = {}
    features.update(_fft_features(gray))
    features.update(_haar_energies(gray))
    features.update(_hog_features(gray))
    features.update(_rgb_features(rgb))
    features.update(_texture_features(gray))

    freq = frequency_analysis(path)
    features.update({
        "legacy_fft_high_low_ratio": _finite(freq.get("high_low_frequency_ratio")),
        "legacy_fft_peak_count": _finite(freq.get("spectral_peak_count")),
        "legacy_fft_quadrant_cv": _finite(freq.get("quadrant_mean_cv")),
    })
    noise = noise_map_analysis(path)
    features.update({
        "noise_residual_std": _finite(noise.get("residual_std")),
        "noise_local_std_mean": _finite(noise.get("local_std_mean")),
        "noise_local_std_cv": _finite(noise.get("local_std_cv")),
    })
    prnu = prnu_screen(path)
    features.update({
        "prnu_like_residual_std": _finite(prnu.get("residual_std")),
        "prnu_like_local_energy_mean": _finite(prnu.get("local_energy_mean")),
        "prnu_like_local_energy_cv": _finite(prnu.get("local_energy_cv")),
    })
    resampling = resampling_analysis(path)
    features.update({
        "resampling_short_lag_persistence": _finite(resampling.get("short_lag_persistence")),
        "resampling_max_autocorrelation": _finite(resampling.get("max_nonzero_autocorrelation")),
    })

    names = sorted(features)
    values = [_finite(features[name]) for name in names]
    family_prefixes = {
        "frequency": ("fft_", "legacy_fft_"), "wavelet": ("wavelet_",), "hog": ("hog_",),
        "rgb": ("rgb_", "hsv_"), "texture": ("texture_",), "noise": ("noise_",),
        "prnu_like": ("prnu_like_",), "resampling": ("resampling_",),
    }
    families = {family: [n for n in names if n.startswith(prefixes)] for family, prefixes in family_prefixes.items()}
    return {
        "status": "success", "schema": SCHEMA, "feature_count": len(names), "feature_names": names,
        "feature_values": values, "features": {name: value for name, value in zip(names, values)},
        "families": families, "calibrated": False,
        "warning": "The feature bank is descriptive, not a classifier. Generator/post-processing dependence requires independent ML validation.",
    }


def extract_synthetic_feature_bank(path: str | Path) -> dict:
    return synthetic_feature_bank(path)
