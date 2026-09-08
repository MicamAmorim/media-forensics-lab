from pathlib import Path
import json
import os
import subprocess
import sys

import cv2

from mf_lab.analysis.deepfake import image_deepfake_protocol
from mf_lab.analysis.image import copy_move_orb
from mf_lab.analysis.video import frame_hash_duplicates, frame_transition_anomalies
from mf_lab.validation import validate_demo

D = Path(__file__).resolve().parents[1] / "dataset" / "demo"


def test_demo_ground_truth_exists():
    p = D / "ground_truth.json"
    assert p.exists()
    gt = json.loads(p.read_text(encoding="utf-8"))
    assert "img_002_copy_move.jpg" in gt["images"]
    assert "img_007_deepfake_face.jpg" in gt["images"]
    assert "img_008_ai_generated.png" in gt["images"]


def test_copy_move_fixture_detects_known_translation():
    gt = json.loads((D / "ground_truth.json").read_text(encoding="utf-8"))
    expected = gt["images"]["img_002_copy_move.jpg"]["expected_translation_px"]
    r = copy_move_orb(D / "images" / "img_002_copy_move.jpg")
    assert r["suspicious_pairs"] >= 10
    assert r["suspicious_cluster_count"] >= 1
    observed = r["dominant_translation_px"]
    assert observed is not None
    assert sum((float(a) - float(b)) ** 2 for a, b in zip(observed, expected)) ** 0.5 <= 8.0


def test_pristine_fixture_has_no_copy_move_cluster():
    r = copy_move_orb(D / "images" / "img_001_pristine.jpg")
    assert r["suspicious_cluster_count"] == 0


def test_duplicated_video_exact_positions():
    gt = json.loads((D / "ground_truth.json").read_text(encoding="utf-8"))
    expected = gt["videos"]["vid_002_duplicated_frames.mp4"]["expected_duplicate_transitions"]
    r = frame_hash_duplicates(D / "videos" / "vid_002_duplicated_frames.mp4")
    assert r["adjacent_near_duplicates"] == expected


def test_pristine_video_has_no_duplicate_transition():
    r = frame_hash_duplicates(D / "videos" / "vid_001_pristine.mp4")
    assert r["duplicate_count"] == 0


def test_overlay_fixture_exact_abrupt_boundaries():
    gt = json.loads((D / "ground_truth.json").read_text(encoding="utf-8"))
    expected = gt["videos"]["vid_004_overlay_edit.mp4"]["expected_abrupt_transitions"]
    r = frame_transition_anomalies(D / "videos" / "vid_004_overlay_edit.mp4")
    got = [x["index"] for x in r["anomalous_transitions"]]
    assert got == expected


def test_pristine_video_has_no_abrupt_transition():
    r = frame_transition_anomalies(D / "videos" / "vid_001_pristine.mp4")
    assert r["anomaly_count"] == 0


def test_pristine_not_escalated_as_deepfake():
    r = image_deepfake_protocol(D / "images" / "img_001_pristine.jpg")
    assert r["triage_assessment"] != "needs_expert_review"
    assert r["evidentiary_conclusion"] == "inconclusive"


def test_validate_demo_harness_passes_supported_checks(tmp_path):
    out = tmp_path / "validation.json"
    r = validate_demo(D, out)
    assert out.exists()
    assert r["summary"]["failed"] == 0
    assert r["summary"]["ready_for_demo_regression"] is True


def test_unicode_path_read_regression(tmp_path):
    target = tmp_path / "Perícia Digital"
    target.mkdir()
    src = D / "images" / "img_001_pristine.jpg"
    copied = target / src.name
    copied.write_bytes(src.read_bytes())
    r = copy_move_orb(copied)
    assert r["keypoints"] > 0


def test_editable_package_import_and_cli_help():
    # A lightweight packaging regression: current checkout must expose the CLI module.
    import mf_lab.cli  # noqa: F401
    p = subprocess.run([sys.executable, "-m", "mf_lab.cli", "--help"], capture_output=True, text=True)
    assert p.returncode == 0
    assert "validate-demo" in p.stdout


def test_windows_haarcascade_unicode_guard():
    if os.name != "nt":
        return
    import cv2
    bogus = r"Z:\Per├¡cia Digital\cv2\data\haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(bogus)
    assert not cascade.empty()


def test_ai_generated_fixture_triggers_synthetic_texture_screen():
    r = image_deepfake_protocol(D / "images" / "img_008_ai_generated.png")
    assert any(x.get("family") == "synthetic_texture" for x in r.get("screening_observations", []))


def test_builtin_c2pa_marker_scanner_is_non_cryptographic(tmp_path):
    from mf_lab.analysis.c2pa import c2pa_inspect
    p = tmp_path / "marker.bin"
    p.write_bytes(b"test-jumb-marker-c2pa-openai")
    r = c2pa_inspect(p)
    if r.get("tool") == "builtin_marker_scan":
        assert r["embedded_c2pa_marker_present"] is True
        assert r["cryptographically_validated"] is False


def test_face_replacement_fixture_triggers_face_screening_flag():
    from mf_lab.analysis.deepfake import face_artifact_screen
    r = face_artifact_screen(D / "images" / "img_007_deepfake_face.jpg")
    flags = set(r.get("screening_flags", []))
    # The fixture must trigger at least one documented facial inconsistency.
    # The exact flag can change with JPEG decoding/OpenCV versions, so this
    # regression avoids overfitting to one boundary metric.
    allowed = {"face_boundary_texture_discontinuity", "face_luminance_texture_inconsistency"}
    assert flags & allowed
