from pathlib import Path

from mf_lab.analysis.fusion import synthetic_evidence_fusion
from mf_lab.analysis.synthetic_features import extract_synthetic_feature_bank
from mf_lab.analysis.synthetic_ml import score_synthetic_ml

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "dataset" / "demo" / "images"


def test_synthetic_feature_bank_is_stable_and_finite():
    r = extract_synthetic_feature_bank(D / "img_001_pristine.jpg")
    assert r["status"] == "success"
    assert r["feature_count"] >= 35
    assert "fft_hf_lf_ratio" in r["features"]
    assert "rgb_corr_rg" in r["features"]
    assert "wavelet_l1_hf_total" in r["features"]
    assert "hog_mean" in r["features"]


def test_ml_detector_is_disabled_without_explicit_model(monkeypatch):
    monkeypatch.delenv("MFLAB_SYNTHETIC_MODEL", raising=False)
    r = score_synthetic_ml({"features": {"x": 1.0}})
    assert r["status"] == "not_configured"
    assert r["validated"] is False


def test_fusion_never_returns_evidentiary_verdict():
    r = synthetic_evidence_fusion({
        "synthetic_spectral": {"screening_flags": ["x"]},
        "face_context_consistency": {"screening_flags": ["y"]},
        "synthetic_ml": {"status": "success", "validated": True},
    })
    assert r["family_count"] >= 3
    assert r["evidentiary_conclusion"] == "inconclusive"


def test_pipeline_exposes_v05_synthetic_protocol_and_new_methods(tmp_path):
    from mf_lab.pipeline import analyze_file
    r = analyze_file(D / "img_001_pristine.jpg", tmp_path, profile="deepfake")
    assert r["methods"]["deepfake_protocol"]["protocol_version"] == "MFLAB-DF-0.5"
    for name in (
        "synthetic_feature_bank",
        "synthetic_ml",
        "synthetic_deep",
        "face_context_consistency",
        "synthetic_evidence_fusion",
    ):
        assert name in r["methods"]
