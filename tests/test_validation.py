"""Controlled ground-truth regression tests.

These tests check known injected transformations in dataset/demo. They are not
estimates of real-world forensic error rates.
"""
from pathlib import Path
import json
import math

from mf_lab.analysis.classical import resampling_analysis
from mf_lab.analysis.deepfake import image_deepfake_protocol
from mf_lab.analysis.image import copy_move_orb
from mf_lab.analysis.video import frame_hash_duplicates, frame_transition_anomalies
from mf_lab.validation import validate_demo

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "dataset" / "demo"
GT = json.loads((D / "ground_truth.json").read_text(encoding="utf-8"))


def test_copy_move_detects_injected_translation():
    expected = GT["images"]["img_002_copy_move.jpg"]["expected_translation_px"]
    r = copy_move_orb(D / "images" / "img_002_copy_move.jpg")
    assert r["suspicious_pairs"] >= 10
    assert r["suspicious_cluster_count"] >= 1
    assert math.dist(expected, r["dominant_translation_px"]) <= 8.0


def test_pristine_has_no_copy_move_cluster():
    r = copy_move_orb(D / "images" / "img_001_pristine.jpg")
    assert r["suspicious_cluster_count"] == 0


def test_resampling_fixture_separates_from_pristine():
    pristine = resampling_analysis(D / "images" / "img_001_pristine.jpg")
    resampled = resampling_analysis(D / "images" / "img_005_resampled.jpg")
    assert pristine["screening_flag"] is False
    assert resampled["screening_flag"] is True


def test_duplicate_frames_exact_fixture_positions():
    expected = GT["videos"]["vid_002_duplicated_frames.mp4"]["expected_duplicate_transitions"]
    r = frame_hash_duplicates(D / "videos" / "vid_002_duplicated_frames.mp4")
    assert r["adjacent_near_duplicates"] == expected


def test_overlay_abrupt_boundaries_detected():
    expected = GT["videos"]["vid_004_overlay_edit.mp4"]["expected_abrupt_transitions"]
    r = frame_transition_anomalies(D / "videos" / "vid_004_overlay_edit.mp4")
    observed = [x["index"] for x in r["anomalous_transitions"]]
    assert observed == expected


def test_pristine_video_has_no_abrupt_transition_flag():
    r = frame_transition_anomalies(D / "videos" / "vid_001_pristine.mp4")
    assert r["anomaly_count"] == 0


def test_pristine_image_not_escalated_as_deepfake():
    r = image_deepfake_protocol(D / "images" / "img_001_pristine.jpg")
    assert r["triage_assessment"] != "needs_expert_review"
    assert r["validated_external_models"] == 0


def test_demo_validation_harness_passes_required_regressions(tmp_path):
    out = tmp_path / "validation.json"
    r = validate_demo(D, out)
    assert r["summary"]["failed"] == 0
    assert r["summary"]["ready_for_demo_regression"] is True
    assert r["summary"]["unsupported"] == 3
    assert out.exists()
