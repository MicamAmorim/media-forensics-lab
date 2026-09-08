from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

from mf_lab.pipeline import analyze_file
from mf_lab.utils.io import write_json


def _check(name: str, passed: bool, **details) -> dict:
    return {"check": name, "status": "pass" if passed else "fail", **details}


def _unsupported(name: str, reason: str) -> dict:
    return {"check": name, "status": "unsupported", "reason": reason}


def _distance(a, b) -> float | None:
    if a is None or b is None or len(a) != len(b):
        return None
    return float(math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b))))


def validate_demo(dataset_dir: str | Path | None = None, out_path: str | Path | None = None) -> dict:
    """Run controlled regression validation against the bundled demo ground truth.

    This deliberately does *not* estimate real-world sensitivity/specificity.
    The fixture is tiny, synthetic and partly used to regression-test engineering
    thresholds. Results answer only whether known injected manipulations exercise
    the intended code paths without obvious pristine false escalation.
    """
    root = Path(__file__).resolve().parents[1]
    dataset = Path(dataset_dir) if dataset_dir else root / "dataset" / "demo"
    gt = json.loads((dataset / "ground_truth.json").read_text(encoding="utf-8"))

    reports: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="mflab-validation-") as tmp:
        tmp_path = Path(tmp)
        for kind, subdir in (("images", "images"), ("videos", "videos")):
            for name in gt.get(kind, {}):
                reports[name] = analyze_file(dataset / subdir / name, tmp_path, profile="full")

    checks: list[dict] = []

    # Pristine image: native uncalibrated synthetic-media heuristics must not
    # automatically escalate it to a deepfake-specific expert-review verdict.
    pristine_img = reports.get("img_001_pristine.jpg", {})
    p_methods = pristine_img.get("methods", {})
    p_proto = p_methods.get("deepfake_protocol", {})
    checks.append(_check(
        "pristine_image_not_deepfake_escalated",
        p_proto.get("triage_assessment") != "needs_expert_review",
        observed=p_proto.get("triage_assessment"),
        expected="not needs_expert_review",
    ))
    checks.append(_check(
        "pristine_image_no_copy_move_cluster",
        int(p_methods.get("copy_move_orb", {}).get("suspicious_cluster_count", 0) or 0) == 0,
        observed=p_methods.get("copy_move_orb", {}).get("suspicious_cluster_count"),
        expected=0,
    ))

    # Copy-move: require a coherent cluster and recover the known translation.
    cm_gt = gt.get("images", {}).get("img_002_copy_move.jpg", {})
    cm = reports.get("img_002_copy_move.jpg", {}).get("methods", {}).get("copy_move_orb", {})
    expected_translation = cm_gt.get("expected_translation_px")
    observed_translation = cm.get("dominant_translation_px")
    translation_error = _distance(expected_translation, observed_translation)
    checks.append(_check(
        "copy_move_detected",
        int(cm.get("suspicious_pairs", 0) or 0) >= 10 and int(cm.get("suspicious_cluster_count", 0) or 0) >= 1,
        suspicious_pairs=cm.get("suspicious_pairs"),
        suspicious_clusters=cm.get("suspicious_cluster_count"),
    ))
    checks.append(_check(
        "copy_move_translation_matches_fixture",
        translation_error is not None and translation_error <= 8.0,
        expected_translation_px=expected_translation,
        observed_translation_px=observed_translation,
        error_px=translation_error,
        tolerance_px=8.0,
    ))

    # Double JPEG: the current DCT heuristic is not a calibrated classifier, so
    # validate only that the injected double-compression fixture ranks well above
    # the pristine baseline. This is a diagnostic regression, not an error rate.
    pristine_dct = float(p_methods.get("jpeg_dct", {}).get("score", 0.0) or 0.0)
    double_dct = float(reports.get("img_004_double_jpeg.jpg", {}).get("methods", {}).get("jpeg_dct", {}).get("score", 0.0) or 0.0)
    ratio = double_dct / (pristine_dct + 1e-12)
    checks.append(_check(
        "double_jpeg_dct_ranks_above_pristine",
        double_dct > pristine_dct + 0.05 and ratio >= 2.0,
        pristine_score=pristine_dct,
        double_jpeg_score=double_dct,
        ratio=ratio,
        claim="diagnostic ranking only; not a calibrated double-JPEG verdict",
    ))

    # Resampling: use the revised short-lag persistence flag, not raw lag-1 AC.
    pristine_resampling = p_methods.get("resampling", {})
    resampled = reports.get("img_005_resampled.jpg", {}).get("methods", {}).get("resampling", {})
    checks.append(_check(
        "resampling_fixture_separates_from_pristine",
        pristine_resampling.get("screening_flag") is False and resampled.get("screening_flag") is True,
        pristine_persistence=pristine_resampling.get("short_lag_persistence"),
        resampled_persistence=resampled.get("short_lag_persistence"),
        threshold=resampled.get("screening_threshold"),
        claim="screening regression only; not population calibration",
    ))

    # Pristine video sanity checks.
    pv = reports.get("vid_001_pristine.mp4", {}).get("methods", {})
    checks.append(_check(
        "pristine_video_no_duplicate_or_abrupt_transition_flag",
        int(pv.get("video_duplicates", {}).get("duplicate_count", 0) or 0) == 0
        and int(pv.get("video_transition_anomalies", {}).get("anomaly_count", 0) or 0) == 0,
        duplicate_count=pv.get("video_duplicates", {}).get("duplicate_count"),
        abrupt_transition_count=pv.get("video_transition_anomalies", {}).get("anomaly_count"),
    ))

    # Exact duplicated transitions are known by construction.
    dup_gt = gt.get("videos", {}).get("vid_002_duplicated_frames.mp4", {})
    dup = reports.get("vid_002_duplicated_frames.mp4", {}).get("methods", {}).get("video_duplicates", {})
    expected_dup = dup_gt.get("expected_duplicate_transitions", [])
    observed_dup = dup.get("adjacent_near_duplicates", [])
    checks.append(_check(
        "duplicated_frames_exact_fixture_positions",
        observed_dup == expected_dup,
        expected=expected_dup,
        observed=observed_dup,
    ))

    # Overlay edit is deliberately abrupt at entry/exit boundaries.
    ov_gt = gt.get("videos", {}).get("vid_004_overlay_edit.mp4", {})
    ov = reports.get("vid_004_overlay_edit.mp4", {}).get("methods", {}).get("video_transition_anomalies", {})
    expected_ov = ov_gt.get("expected_abrupt_transitions", [])
    observed_ov = [x.get("index") for x in ov.get("anomalous_transitions", [])]
    checks.append(_check(
        "overlay_edit_abrupt_boundaries_detected",
        all(x in observed_ov for x in expected_ov) and len(observed_ov) == len(expected_ov),
        expected=expected_ov,
        observed=observed_ov,
    ))

    # These fixtures are intentionally retained as known capability gaps until
    # dedicated validated detectors are added.
    checks.extend([
        _unsupported("splice_localization", "No dedicated validated splice localizer is integrated yet."),
        _unsupported("classical_inpainting_localization", "No dedicated validated inpainting localizer is integrated yet."),
        _unsupported("segment_deletion_after_reencode", "Timestamp continuity is restored by re-encoding; content/motion continuity detector is not yet integrated."),
    ])

    required = [c for c in checks if c["status"] != "unsupported"]
    failed = [c for c in required if c["status"] == "fail"]
    unsupported = [c for c in checks if c["status"] == "unsupported"]
    result = {
        "schema_version": "0.3",
        "dataset": str(dataset),
        "ground_truth_note": gt.get("note"),
        "scope": "controlled regression validation; not real-world forensic validation",
        "checks": checks,
        "summary": {
            "required_checks": len(required),
            "passed": sum(c["status"] == "pass" for c in required),
            "failed": len(failed),
            "unsupported": len(unsupported),
            "ready_for_demo_regression": len(failed) == 0,
        },
        "unsupported_capabilities": [c["check"] for c in unsupported],
        "interpretation": (
            "Passing this harness means the bundled fixtures produce the expected regression behavior. "
            "It does not establish sensitivity, specificity, false-positive rate, courtroom validity, or robustness to unseen domains."
        ),
    }
    if out_path is not None:
        write_json(Path(out_path), result)
    return result
