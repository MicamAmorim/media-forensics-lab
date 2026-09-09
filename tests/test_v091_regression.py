from __future__ import annotations

import json
from pathlib import Path

from mf_lab.analysis.c2pa import _validation_summary
from mf_lab.analysis.deepfake_v2 import image_deepfake_protocol_v2

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "regression" / "openai_synthetic_20260909.json"


def test_openai_synthetic_false_negative_is_escalated_without_becoming_verdict():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    observed = fixture["observed"]
    precomputed = {
        "synthetic_ml": observed["synthetic_ml"],
        "synthetic_evidence_fusion": observed["synthetic_evidence_fusion"],
        "synthetic_spectral": {"screening_flags": ["high_spectral_quadrant_symmetry"]},
        "face_artifacts": {"screening_flags": ["face_boundary_texture_discontinuity"]},
        "face_context_consistency": {"screening_flags": ["face_context_sharpness_mismatch"]},
        "c2pa": observed["c2pa"],
        "noise_map": {"local_std_cv": 0.43},
        "resampling": {"screening_flag": True},
        "prnu_screen": {"local_energy_cv": 0.44, "residual_std": 0.0194},
    }
    result = image_deepfake_protocol_v2("not-read-because-precomputed.png", precomputed=precomputed)

    assert fixture["ground_truth"]["class"] == "synthetic"
    assert result["machine_assessment"]["label"] == "real"
    assert result["machine_assessment"]["validated_for_input"] is False
    assert result["triage_assessment"] == "needs_expert_review"
    assert "cross_family_convergence:moderate_convergence_for_expert_review" in result["review_reasons"]
    assert result["evidence_families"] == []
    assert result["evidentiary_conclusion"] == "inconclusive"


def test_c2pa_summary_requires_signature_validation_and_no_failures():
    valid = {
        "active_manifest": "urn:test",
        "manifests": {"urn:test": {"validation_state": "Trusted", "claim_generator_info": [{"name": "OpenAI Media Service"}]}},
        "validation_results": {
            "activeManifest": {
                "success": [
                    {"code": "claimSignature.validated"},
                    {"code": "assertion.dataHash.match"}
                ],
                "failure": []
            }
        }
    }
    out = _validation_summary(valid, "test")
    assert out["cryptographically_validated"] is True
    assert out["signature_validated"] is True
    assert out["data_hash_validated"] is True
    assert out["producer_hint"] == "OpenAI Media Service"

    invalid = json.loads(json.dumps(valid))
    invalid["manifests"]["urn:test"]["validation_state"] = "Invalid"
    invalid["validation_results"]["activeManifest"]["failure"] = [{"code": "claimSignature.mismatch"}]
    out2 = _validation_summary(invalid, "test")
    assert out2["cryptographically_validated"] is False
    assert out2["status"] == "invalid"
