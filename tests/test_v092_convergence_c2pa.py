from __future__ import annotations

from mf_lab.analysis.c2pa import _validation_summary
from mf_lab.benchmark.convergence import binary_metrics


def test_c2pa_diagnostics_separate_integrity_from_trust():
    base = {
        "active_manifest": "urn:test",
        "manifests": {
            "urn:test": {
                "claim_generator": "Example/1.0",
                "claim_generator_info": [{"name": "OpenAI Media Service", "version": "1"}],
                "title": "asset.png",
                "signature_info": {
                    "alg": "Es256",
                    "issuer": "Example Issuer",
                    "time": "2026-09-09T00:00:00Z",
                },
                "assertions": [
                    {"label": "c2pa.actions", "data": {}},
                    {"label": "c2pa.hash.data", "data": {}},
                ],
            }
        },
    }
    results = {
        "activeManifest": {
            "success": [
                {"code": "claimSignature.validated", "explanation": "signature valid"},
                {"code": "assertion.dataHash.match"},
            ],
            "failure": [],
        }
    }

    valid_untrusted = _validation_summary(
        base,
        "test",
        validation_state="Valid",
        validation_results=results,
        embedded=True,
    )
    assert valid_untrusted["status"] == "validated"
    assert valid_untrusted["integrity_validated"] is True
    assert valid_untrusted["cryptographically_validated"] is True
    assert valid_untrusted["signature_trusted"] is False
    assert valid_untrusted["trust_status"] == "valid_but_not_trusted"
    assert valid_untrusted["manifest_location"] == "embedded"
    assert valid_untrusted["validation_failure_count"] == 0
    assert valid_untrusted["validation_success_count"] == 2
    assert valid_untrusted["producer_hint"] == "OpenAI Media Service"
    assert valid_untrusted["signature_info"]["issuer"] == "Example Issuer"
    assert "c2pa.actions" in valid_untrusted["assertion_labels"]

    trusted = _validation_summary(
        base,
        "test",
        validation_state="Trusted",
        validation_results=results,
        embedded=True,
    )
    assert trusted["integrity_validated"] is True
    assert trusted["signature_trusted"] is True
    assert trusted["trust_status"] == "trusted"


def test_c2pa_invalid_state_preserves_failure_explanation():
    data = {
        "active_manifest": "urn:test",
        "manifests": {"urn:test": {"claim_generator": "Example/1.0"}},
    }
    results = {
        "activeManifest": {
            "success": [{"code": "assertion.dataHash.match"}],
            "failure": [
                {
                    "code": "claimSignature.mismatch",
                    "explanation": "signature does not match claim",
                    "url": "self#jumbf=/c2pa/test",
                }
            ],
        }
    }
    out = _validation_summary(
        data,
        "test",
        validation_state="Invalid",
        validation_results=results,
    )
    assert out["status"] == "invalid"
    assert out["integrity_validated"] is False
    assert out["signature_trusted"] is False
    assert out["trust_status"] == "invalid"
    assert out["validation_failure_count"] == 1
    assert out["validation_failures"] == ["claimSignature.mismatch"]
    failure = [x for x in out["validation_statuses"] if x["kind"] == "failure"][0]
    assert failure["explanation"] == "signature does not match claim"
    assert failure["url"] == "self#jumbf=/c2pa/test"


def test_binary_metrics_report_sensitivity_specificity_and_error_rates():
    rows = [
        {"expected_synthetic": True, "fusion_review": True},
        {"expected_synthetic": True, "fusion_review": False},
        {"expected_synthetic": False, "fusion_review": True},
        {"expected_synthetic": False, "fusion_review": False},
        {"expected_synthetic": False, "fusion_review": False},
    ]
    metrics = binary_metrics(rows, "fusion_review")
    assert metrics["confusion_matrix"] == {"tn": 2, "fp": 1, "fn": 1, "tp": 1}
    assert metrics["sensitivity"] == 0.5
    assert metrics["specificity"] == 2 / 3
    assert metrics["false_positive_rate"] == 1 / 3
    assert metrics["false_negative_rate"] == 0.5
    assert metrics["accuracy"] == 3 / 5
    assert metrics["sensitivity_wilson_95"] is not None
    assert metrics["specificity_wilson_95"] is not None
