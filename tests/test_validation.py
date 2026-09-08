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
from mf_lab.analysis.video import frame_hash_duplicates, frame_transition_anomalies, motion_discontinuity_screen
from mf_lab.analysis.reference import reference_image_difference, reference_video_sequence_alignment
from mf_lab.validation import validate_demo

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "dataset" / "demo"
GT = json.loads((D / "ground_truth.json").read_text(encoding="utf-8"))


def test_every_ground_truth_fixture_declares_required_checks():
    for kind in ("images", "videos"):
        assert GT[kind], f"GT section {kind} must not be empty"
        for name, meta in GT[kind].items():
            checks = meta.get("required_checks")
            assert isinstance(checks, list) and checks, f"{name} has no required_checks"
            assert len(checks) == len(set(checks)), f"{name} has duplicate required_checks"


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


def test_demo_validation_harness_is_exactly_100_percent_against_gt(tmp_path):
    out = tmp_path / "validation.json"
    r = validate_demo(D, out)
    s = r["summary"]
    assert s["gt_contract_errors"] == 0
    assert s["unsupported"] == 0
    assert s["failed"] == 0
    assert s["gt_fixture_coverage_pct"] == 100.0
    assert s["gt_fixture_pass_rate_pct"] == 100.0
    assert s["gt_assertion_coverage_pct"] == 100.0
    assert s["gt_pass_rate_pct"] == 100.0
    assert s["gt_fixture_count"] == len(GT["images"]) + len(GT["videos"])
    assert s["gt_required_assertions"] == sum(
        len(meta["required_checks"])
        for kind in ("images", "videos")
        for meta in GT[kind].values()
    )
    assert s["ready_for_demo_regression"] is True
    assert out.exists()


def _bbox_iou(a, b):
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    x1=max(ax,bx); y1=max(ay,by); x2=min(ax+aw,bx+bw); y2=min(ay+ah,by+bh)
    inter=max(0,x2-x1)*max(0,y2-y1)
    union=aw*ah+bw*bh-inter
    return inter/union if union else 0


def test_splice_reference_localization():
    gt=GT["images"]["img_003_splice.jpg"]
    r=reference_image_difference(D/"images"/"img_003_splice.jpg", D/"images"/gt["reference"])
    assert _bbox_iou(r["largest_component_bbox_xywh"], gt["expected_bbox_xywh"]) >= 0.75


def test_inpainting_reference_localization():
    gt=GT["images"]["img_006_inpainted.jpg"]
    r=reference_image_difference(D/"images"/"img_006_inpainted.jpg", D/"images"/gt["reference"])
    assert _bbox_iou(r["largest_component_bbox_xywh"], gt["expected_bbox_xywh"]) >= 0.45


def test_face_replacement_reference_localization():
    gt=GT["images"]["img_007_deepfake_face.jpg"]
    r=reference_image_difference(D/"images"/"img_007_deepfake_face.jpg", D/"images"/gt["reference"])
    assert _bbox_iou(r["largest_component_bbox_xywh"], gt["face_bbox_xywh"]) >= 0.50


def test_ai_generated_native_synthetic_texture_screen():
    r=image_deepfake_protocol(D/"images"/"img_008_ai_generated.png")
    assert any(x.get("family") == "synthetic_texture" for x in r.get("screening_observations", []))


def test_segment_deletion_motion_discontinuity():
    gt=GT["videos"]["vid_003_deleted_segment.mp4"]
    r=motion_discontinuity_screen(D/"videos"/"vid_003_deleted_segment.mp4")
    assert gt["expected_questioned_transition_index"] in [x["index"] for x in r["anomalies"]]


def test_segment_deletion_reference_alignment():
    gt=GT["videos"]["vid_003_deleted_segment.mp4"]
    r=reference_video_sequence_alignment(D/"videos"/"vid_003_deleted_segment.mp4", D/"videos"/gt["reference"])
    assert any(x["skipped_reference_count"] == len(gt["deleted_source_frames"]) and [x["previous_reference_index"],x["next_reference_index"]] == gt["expected_reference_jump"] for x in r["skipped_segments"])
