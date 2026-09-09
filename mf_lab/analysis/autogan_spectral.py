from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from mf_lab.utils.io import cv_imread


AUTOGAN_INPUT_SIZE = 256
AUTOGAN_CROP_SIZE = 224
AUTOGAN_MODES = {"full": 0, "low": 1, "mid": 2, "high": 3}


def _prepare_rgb(path: str | Path) -> np.ndarray:
    """Prepare a 224x224 RGB crop compatible with the AutoGAN detector pipeline.

    The original implementation operates on 256x256 samples and uses the central
    224x224 crop for ResNet-family detectors. We reproduce that geometry without
    importing or copying the upstream implementation.
    """
    bgr = cv_imread(path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"unreadable image: {path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    if rgb.shape[:2] != (AUTOGAN_INPUT_SIZE, AUTOGAN_INPUT_SIZE):
        interpolation = cv2.INTER_AREA if max(rgb.shape[:2]) > AUTOGAN_INPUT_SIZE else cv2.INTER_CUBIC
        rgb = cv2.resize(rgb, (AUTOGAN_INPUT_SIZE, AUTOGAN_INPUT_SIZE), interpolation=interpolation)
    margin = (AUTOGAN_INPUT_SIZE - AUTOGAN_CROP_SIZE) // 2
    rgb = rgb[margin:margin + AUTOGAN_CROP_SIZE, margin:margin + AUTOGAN_CROP_SIZE]
    return rgb.astype(np.float32) / 255.0


def _normalize_log_spectrum(channel: np.ndarray) -> np.ndarray:
    spectrum = np.fft.fft2(channel)
    log_mag = np.log(np.abs(spectrum) + 1e-3).astype(np.float32)
    p5, p95 = np.percentile(log_mag, [5, 95])
    if not np.isfinite(p5) or not np.isfinite(p95) or p95 <= p5:
        return np.zeros_like(log_mag, dtype=np.float32)
    normalized = (log_mag - float(p5)) / float(p95 - p5)
    normalized = (normalized - 0.5) * 2.0
    return np.clip(normalized, -1.0, 1.0).astype(np.float32)


def _band_mask(size: int, mode: str) -> np.ndarray:
    if mode not in AUTOGAN_MODES:
        raise ValueError(f"unsupported AutoGAN spectral mode: {mode}")
    mask = np.ones((size, size), dtype=np.float32)
    if mode == "full":
        return mask

    # These boundaries reproduce the low/mid/high partitions used by the
    # published AutoGAN code for the 224x224 central crop.
    if size == 224:
        inner_lo, inner_hi = 57, 177
        outer_lo, outer_hi = 21, 203
    else:
        # Relative fallback for tests/future experimentation.
        inner_lo, inner_hi = int(round(size * 57 / 224)), int(round(size * 177 / 224))
        outer_lo, outer_hi = int(round(size * 21 / 224)), int(round(size * 203 / 224))

    mask.fill(0.0)
    if mode == "low":
        mask[inner_lo:inner_hi, inner_lo:inner_hi] = 1.0
    elif mode == "mid":
        mask[outer_lo:outer_hi, outer_lo:outer_hi] = 1.0
        mask[inner_lo:inner_hi, inner_lo:inner_hi] = 0.0
    elif mode == "high":
        mask.fill(1.0)
        mask[outer_lo:outer_hi, outer_lo:outer_hi] = 0.0
    return mask


def autogan_spectral_tensor(path: str | Path, mode: str = "full") -> np.ndarray:
    """Return the clean-room AutoGAN-compatible spectral tensor [3,224,224].

    Values are log-FFT magnitudes normalized with P5/P95 and clipped to [-1,1],
    matching the scientific preprocessing described and implemented upstream.
    Band selection is applied in the centered frequency plane and the tensor is
    returned in the unshifted orientation expected by the original classifier.
    """
    rgb = _prepare_rgb(path)
    channels = []
    for idx in range(3):
        full = _normalize_log_spectrum(rgb[:, :, idx])
        shifted = np.fft.fftshift(full)
        shifted = shifted * _band_mask(shifted.shape[0], mode)
        channels.append(np.fft.ifftshift(shifted).astype(np.float32))
    return np.stack(channels, axis=0)


def autogan_visual_spectrum(path: str | Path, mode: str = "full") -> np.ndarray:
    """Return a centered uint8 RGB visualization of an AutoGAN spectral tensor."""
    tensor = autogan_spectral_tensor(path, mode=mode)
    centered = np.stack([np.fft.fftshift(tensor[i]) for i in range(3)], axis=2)
    return np.clip((centered + 1.0) * 127.5, 0, 255).astype(np.uint8)


def _profile_autocorrelation_peak(profile: np.ndarray) -> tuple[float, int]:
    x = np.asarray(profile, dtype=np.float64)
    if x.size < 8 or not np.isfinite(x).all():
        return 0.0, 0
    x = x - float(x.mean())
    denom = float(np.dot(x, x))
    if denom <= 1e-12:
        return 0.0, 0
    corr = np.correlate(x, x, mode="full")[x.size - 1:] / denom
    start = max(2, x.size // 64)
    stop = max(start + 1, x.size // 2)
    window = corr[start:stop]
    if window.size == 0:
        return 0.0, 0
    pos = int(np.argmax(window))
    return float(window[pos]), int(start + pos)


def _quadrant_replication_score(centered: np.ndarray) -> float:
    n = centered.shape[0]
    h = n // 2
    q1 = centered[:h, :h].ravel()
    q2 = centered[:h, -h:].ravel()
    q3 = centered[-h:, :h].ravel()
    q4 = centered[-h:, -h:].ravel()
    scores = []
    for a, b in ((q1, q2), (q1, q3), (q1, q4), (q2, q3), (q2, q4), (q3, q4)):
        sa, sb = float(np.std(a)), float(np.std(b))
        if sa <= 1e-8 or sb <= 1e-8:
            continue
        scores.append(abs(float(np.corrcoef(a, b)[0, 1])))
    return float(np.mean(scores)) if scores else 0.0


def autogan_spectral_analysis(path: str | Path) -> dict:
    """Descriptive GAN-upsampling spectral analysis inspired by AutoGAN.

    This method deliberately does not convert spectral descriptors into a
    fake/real decision. The original AutoGAN contribution uses a learned
    spectrum classifier; classification is handled separately by the optional
    integration adapter and must retain its own validation metadata.
    """
    full = autogan_spectral_tensor(path, mode="full")
    features: dict[str, float] = {}

    band_energy: dict[str, float] = {}
    for mode in AUTOGAN_MODES:
        tensor = autogan_spectral_tensor(path, mode=mode)
        abs_tensor = np.abs(tensor)
        band_energy[mode] = float(np.mean(abs_tensor))
        features[f"autogan_{mode}_mean_abs"] = band_energy[mode]
        features[f"autogan_{mode}_std"] = float(np.std(tensor))

    total = max(band_energy["low"] + band_energy["mid"] + band_energy["high"], 1e-12)
    for mode in ("low", "mid", "high"):
        features[f"autogan_{mode}_energy_fraction"] = float(band_energy[mode] / total)

    centered_mean = np.mean(np.abs(np.stack([np.fft.fftshift(full[i]) for i in range(3)], axis=0)), axis=0)
    px = np.mean(centered_mean, axis=0)
    py = np.mean(centered_mean, axis=1)
    peak_x, lag_x = _profile_autocorrelation_peak(px)
    peak_y, lag_y = _profile_autocorrelation_peak(py)
    features["autogan_replication_autocorr_peak_x"] = peak_x
    features["autogan_replication_autocorr_peak_y"] = peak_y
    features["autogan_replication_lag_x"] = float(lag_x)
    features["autogan_replication_lag_y"] = float(lag_y)
    features["autogan_quadrant_replication_score"] = _quadrant_replication_score(centered_mean)

    # Per-channel descriptive summaries retain information useful for later ML
    # without asserting a universal engineering threshold.
    for idx, name in enumerate(("r", "g", "b")):
        centered = np.fft.fftshift(full[idx])
        features[f"autogan_{name}_mean"] = float(np.mean(centered))
        features[f"autogan_{name}_std"] = float(np.std(centered))
        features[f"autogan_{name}_abs_p95"] = float(np.percentile(np.abs(centered), 95))

    return {
        "status": "success",
        "method": "autogan_spectral",
        "feature_family": "gan_upsampling_spectral_artifacts",
        "implementation": "independent_clean_room_reproduction",
        "source_method": "Zhang, Karaman and Chang, WIFS 2019",
        "input_geometry": [AUTOGAN_CROP_SIZE, AUTOGAN_CROP_SIZE, 3],
        "normalization": "per-channel log(abs(FFT)+1e-3), P5/P95 scaling to [-1,1]",
        "bands": ["full", "low", "mid", "high"],
        "features": features,
        "feature_count": len(features),
        "screening_flags": [],
        "screening_only": True,
        "validated": False,
        "calibrated": False,
        "method_scope": "Artifacts associated with GAN upsampling pipelines; absence does not exclude GAN generation and does not address diffusion generators in general.",
        "warning": "AutoGAN-compatible spectral descriptors are explanatory features, not a universal AI detector or posterior probability.",
    }
