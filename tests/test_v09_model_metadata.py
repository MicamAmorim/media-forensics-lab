import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_META = ROOT / "mf_lab" / "models" / "mflab_cifake_hgb_calibrated_v1.json"
RESULT = ROOT / "validation" / "scientific" / "CIFAKE_V09_RESULT.json"


def test_bundled_model_metadata_matches_validation_report():
    meta = json.loads(MODEL_META.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert meta["model_name"] == result["model"]["name"]
    assert meta["sha256"] == result["model"]["model_sha256"]
    assert meta["feature_count"] == result["model"]["feature_count"] == 73
    assert meta["decision_threshold"] == result["model"]["decision_threshold"] == 0.5
    assert meta["calibrated"] is True
    assert meta["validated"] is True
    assert result["primary_fresh_holdout"]["metrics"]["n"] == 10000
    assert result["splits"]["fit_count"] == 90000
    assert result["forensic_policy"]["automatic_label_is_evidentiary_conclusion"] is False
