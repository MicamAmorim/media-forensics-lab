from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from skimage.feature import graycomatrix, graycoprops, hog, local_binary_pattern

from mf_lab.analysis.autogan_spectral import autogan_spectral_analysis
from mf_lab.utils.io import cv_imread


def _read_rgb(path: str | Path) -> np.ndarray:
    bgr = cv_imread(path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"unreadable image: {path}")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def _haar_energies(gray: np.ndarray, levels: int = 3) -> dict[str, float]:
    x = gray.astype(np.float32) / 255.0
    out: dict[str, float] = {}
    for level in range(1, levels + 1):
        h, w = x.shape
        h -= h % 2
        w -= w % 2
        if h < 4 or w < 4:
            break
        x = x[:h, :w]
        a = x[0::2, 0::2]
        b = x[0::2, 1::2]
        c = x[1::2, 0::2]
        d = x[1::2, 1::2]
        ll = (a + b + c + d) * 0.5
        lh = (a - b + c - d) * 0.5
        hl = (a + b - c - d) * 0.5
        hh = (a - b - c + d) * 0.5
        out[f"wavelet_l{level}_lh_energy"] = float(np.mean(lh * lh))
        out[f"wavelet_l{level}_hl_energy"] = float(np.mean(hl * hl))
        out[f"wavelet_l{level}_hh_energy"] = float(np.mean(hh * hh))
        out[f"wavelet_l{level}_hf_total"] = float(np.mean(lh * lh + hl * hl + hh * hh))
        x = ll
    return out


def _rgb_correlations(rgb: np.ndarray) -> dict[str, float]:
    flat = rgb.reshape(-1, 3).astype(np.float64)
    names = ((0, 1, "rg"), (0, 2, "rb"), (1, 2, "gb"))
    result = {}
    for a, b, name in names:
        xa, xb = flat[:, a], flat[:, b]
        denom = xa.std() * xb.std()
        result[f"rgb_corr_{name}"] = float(np.corrcoef(xa, xb)[0, 1]) if denom > 1e-12 else 0.0
    return result


def _texture_features(gray: np.ndarray) -> dict[str, float]:
    small = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA)
    quant = np.clip((small.astype(np.float32) / 256.0 * 16).astype(np.uint8), 0, 15)
    glcm = graycomatrix(
        quant,
        distances=[1, 2],
        angles=[0, np.pi / 4, np.pi / 2],
        levels=16,
        symmetric=True,
        normed=True,
    )
    out = {}
    for prop in ("contrast", "dissimilarity", "homogeneity", "energy", "correlation"):
        out[f"glcm_{prop}"] = float(np.mean(graycoprops(glcm, prop)))
    lbp = local_binary_pattern(small, P=8, R=1, method="uniform")
    hist, _ = np.histogram(lbp, bins=np.arange(0, 11), range=(0, 10), density=True)
    for i, v in enumerate(hist[:10]):
        out[f"lbp_uniform_{i}"] = float(v)
    return out


def _hog_summary(gray: np.ndarray) -> dict[str, float]:
    small = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA)
    vec = hog(
        small,
        orientations=9,
        pixels_per_cell=(16, 16),
        cells_per_block=(2, 2),
        block_norm="L2-Hys",
        feature_vector=True,
    )
    return {
        "hog_mean": float(np.mean(vec)),
        "hog_std": float(np.std(vec)),
        "hog_p90": float(np.percentile(vec, 90)),
        "hog_sparsity": float(np.mean(vec < 1e-3)),
    }


def extract_synthetic_feature_bank(path: str | Path) -> dict:
    """Extract explainable handcrafted features for synthetic-media research.

    v2 extends the original MFLab bank with clean-room AutoGAN-compatible
    spectral descriptors. The feature bank remains descriptive until paired with
    a separately trained and scientifically validated classifier.
    """
    rgb = _read_rgb(path)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    features: dict[str, float] = {}
    features.update(_haar_energies(gray))
    features.update(_rgb_correlations(rgb))
    features.update(_texture_features(gray))
    features.update(_hog_summary(gray))

    f = np.fft.fftshift(np.fft.fft2(gray.astype(np.float32) - float(gray.mean())))
    mag = np.log1p(np.abs(f))
    h, w = mag.shape
    cy, cx = h // 2, w // 2
    yy, xx = np.ogrid[:h, :w]
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    rmax = max(1.0, min(cy, cx))
    bands = []
    for lo, hi in ((0.05, 0.25), (0.25, 0.50), (0.50, 0.75), (0.75, 1.0)):
        m = (rr >= lo * rmax) & (rr < hi * rmax)
        bands.append(float(mag[m].mean()) if np.any(m) else 0.0)
    for i, v in enumerate(bands, 1):
        features[f"fft_band_{i}_mean"] = v
    features["fft_hf_lf_ratio"] = float(bands[-1] / (bands[0] + 1e-12))

    for idx, name in enumerate(("r", "g", "b")):
        ch = rgb[:, :, idx].astype(np.float64)
        mu = float(ch.mean())
        sd = float(ch.std())
        features[f"{name}_mean"] = mu
        features[f"{name}_std"] = sd
        features[f"{name}_skew"] = float(np.mean(((ch - mu) / (sd + 1e-12)) ** 3))

    autogan = autogan_spectral_analysis(path)
    autogan_features = autogan.get("features") or {}
    features.update({k: float(v) for k, v in autogan_features.items()})

    return {
        "status": "success",
        "feature_family": "synthetic_handcrafted_v2",
        "feature_count": len(features),
        "features": features,
        "feature_sources": {
            "mflab_classical_synthetic": len(features) - len(autogan_features),
            "autogan_compatible_spectral": len(autogan_features),
        },
        "calibrated": False,
        "warning": "Feature extraction is descriptive. AutoGAN-compatible descriptors target GAN upsampling artifacts and no single feature is a probability of AI generation.",
    }
