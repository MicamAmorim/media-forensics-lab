from pathlib import Path

import numpy as np

from mf_lab.analysis.autogan_spectral import autogan_spectral_analysis, autogan_spectral_tensor
from mf_lab.analysis.fusion import synthetic_evidence_fusion
from mf_lab.analysis.synthetic_features import extract_synthetic_feature_bank
from mf_lab.integrations.autogan import score_autogan_checkpoint

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "dataset" / "demo" / "images"


def test_autogan_spectral_tensor_matches_expected_geometry_and_partition():
    path = D / "img_001_pristine.jpg"
    full = autogan_spectral_tensor(path, "full")
    low = autogan_spectral_tensor(path, "low")
    mid = autogan_spectral_tensor(path, "mid")
    high = autogan_spectral_tensor(path, "high")
    assert full.shape == (3, 224, 224)
    assert np.isfinite(full).all()
    assert float(full.min()) >= -1.0
    assert float(full.max()) <= 1.0
    assert np.allclose(full, low + mid + high, atol=1e-6)


def test_autogan_analysis_is_descriptive_and_finite():
    r = autogan_spectral_analysis(D / "img_001_pristine.jpg")
    assert r["status"] == "success"
    assert r["screening_only"] is True
    assert r["validated"] is False
    assert r["screening_flags"] == []
    assert r["feature_count"] >= 20
    assert "autogan_low_energy_fraction" in r["features"]
    assert "autogan_quadrant_replication_score" in r["features"]
    assert all(np.isfinite(float(v)) for v in r["features"].values())


def test_synthetic_feature_bank_contains_autogan_family():
    r = extract_synthetic_feature_bank(D / "img_001_pristine.jpg")
    assert r["feature_family"] == "synthetic_handcrafted_v2"
    assert r["feature_sources"]["autogan_compatible_spectral"] >= 20
    assert "autogan_replication_autocorr_peak_x" in r["features"]


def test_autogan_checkpoint_adapter_is_optional(monkeypatch):
    monkeypatch.delenv("MFLAB_AUTOGAN_CHECKPOINT", raising=False)
    monkeypatch.delenv("MFLAB_AUTOGAN_METADATA", raising=False)
    r = score_autogan_checkpoint(D / "img_001_pristine.jpg")
    assert r["status"] == "not_configured"
    assert r["validated"] is False


def test_validated_autogan_checkpoint_can_join_fusion():
    r = synthetic_evidence_fusion({
        "autogan_spectral": {"status": "success", "screening_flags": []},
        "autogan_classifier": {"status": "success", "validated": True},
    })
    assert "autogan_spectral_model" in r["independent_families"]
    assert r["evidentiary_conclusion"] == "inconclusive"


def test_pipeline_exposes_autogan_and_visual_artifacts(tmp_path, monkeypatch):
    from mf_lab.pipeline import analyze_file

    monkeypatch.delenv("MFLAB_AUTOGAN_CHECKPOINT", raising=False)
    r = analyze_file(D / "img_001_pristine.jpg", tmp_path, profile="deepfake")
    assert r["schema_version"] == "0.7"
    assert r["methods"]["autogan_spectral"]["status"] == "success"
    assert r["methods"]["autogan_classifier"]["status"] == "not_configured"
    assert r["methods"]["deepfake_protocol"]["protocol_version"] == "MFLAB-DF-0.6"
    ids = {x["id"] for x in r["visual_artifacts"]["items"]}
    assert {"autogan_fft_full", "autogan_fft_low", "autogan_fft_mid", "autogan_fft_high", "autogan_spectral_profile"}.issubset(ids)
