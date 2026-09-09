from pathlib import Path

from mf_lab.analysis.fusion import synthetic_evidence_fusion
from mf_lab.analysis.synthetic_features import extract_synthetic_feature_bank
from mf_lab.analysis.synthetic_ml import score_synthetic_ml

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "dataset" / "demo" / "images"


def test_synthetic_feature_bank_is_stable_and_finite():
    r = extract_synthetic_feature_bank(D / "img_001_pristine.jpg")
    assert r["status"] == "success"
    assert r["feature_count"] == 73
    assert "fft_hf_lf_ratio" in r["features"]
    assert "rgb_corr_rg" in r["features"]
    assert "wavelet_l1_hf_total" in r["features"]
    assert "hog_mean" in r["features"]
    assert "autogan_low_energy_fraction" in r["features"]
    assert r["input_shape"][2] == 3


def test_bundled_ml_detector_is_available_but_unvalidated_for_arbitrary_input(monkeypatch):
    monkeypatch.delenv("MFLAB_SYNTHETIC_MODEL", raising=False)
    monkeypatch.delenv("MFLAB_SYNTHETIC_MODEL_DOMAIN_CONFIRMED", raising=False)
    bank = extract_synthetic_feature_bank(D / "img_001_pristine.jpg")
    r = score_synthetic_ml(bank)
    assert r["status"] == "success"
    assert r["model_source"] == "bundled"
    assert r["predicted_label"] in {"real", "synthetic"}
    assert 0.0 <= float(r["score_synthetic"]) <= 1.0
    assert r["calibrated"] is True
    assert r["bundle_validated"] is True
    assert r["validated_for_input"] is False
    assert r["validated"] is False
    assert r["validation_scope_status"] == "unconfirmed"


def test_fusion_never_returns_evidentiary_verdict():
    r = synthetic_evidence_fusion({
        "synthetic_spectral": {"screening_flags": ["x"]},
        "face_context_consistency": {"screening_flags": ["y"]},
        "synthetic_ml": {"status": "success", "validated": True},
    })
    assert r["family_count"] >= 3
    assert r["evidentiary_conclusion"] == "inconclusive"


def test_pipeline_exposes_v09_machine_assessment_and_new_methods(tmp_path, monkeypatch):
    from mf_lab.pipeline import analyze_file

    monkeypatch.delenv("MFLAB_SYNTHETIC_MODEL", raising=False)
    monkeypatch.delenv("MFLAB_SYNTHETIC_MODEL_DOMAIN_CONFIRMED", raising=False)
    r = analyze_file(D / "img_001_pristine.jpg", tmp_path, profile="deepfake")
    proto = r["methods"]["deepfake_protocol"]
    assert proto["protocol_version"] == "MFLAB-DF-0.7"
    assert proto["machine_assessment"]["status"] == "available"
    assert proto["machine_assessment"]["label"] in {"real", "synthetic"}
    assert proto["machine_assessment"]["validated_for_input"] is False
    assert proto["machine_assessment"]["forensic_effect"] == "screening_only"
    assert proto["evidentiary_conclusion"] == "inconclusive"
    for name in (
        "synthetic_feature_bank",
        "synthetic_ml",
        "synthetic_deep",
        "face_context_consistency",
        "autogan_spectral",
        "autogan_classifier",
        "synthetic_evidence_fusion",
    ):
        assert name in r["methods"]
