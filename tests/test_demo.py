from pathlib import Path
import json

from mf_lab.utils.io import sha256
from mf_lab.analysis.image import copy_move_orb, noise_residual_stats
from mf_lab.analysis.video import frame_hash_duplicates
from mf_lab.analysis.classical import histogram_analysis, jpeg_quantization_analysis, prnu_screen
from mf_lab.analysis.deepfake import image_deepfake_protocol, video_deepfake_protocol
from mf_lab.integrations.deepfakebench import load_exported_results
from mf_lab.pipeline import analyze_file

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "dataset" / "demo"


def test_dataset_exists():
    assert (D / "ground_truth.json").exists()


def test_hash_is_stable():
    p = D / "images" / "img_001_pristine.jpg"
    assert sha256(p) == sha256(p)
    assert len(sha256(p)) == 64


def test_noise_residual_runs():
    r = noise_residual_stats(D / "images" / "img_001_pristine.jpg")
    assert r["std"] > 0


def test_histogram_runs():
    r = histogram_analysis(D / "images" / "img_001_pristine.jpg")
    assert set(r["channels"]) == {"R", "G", "B"}


def test_jpeg_quantization_available():
    r = jpeg_quantization_analysis(D / "images" / "img_001_pristine.jpg")
    assert r["available"] is True
    assert r["table_count"] >= 1


def test_prnu_is_explicitly_screening_only():
    r = prnu_screen(D / "images" / "img_001_pristine.jpg")
    assert r["status"] == "screening_only"
    assert "not source-camera identification" in r["warning"].lower()


def test_copy_move_screening_runs():
    r = copy_move_orb(D / "images" / "img_002_copy_move.jpg")
    assert r["keypoints"] > 0
    assert r["status"] == "screening_only"


def test_duplicate_frames_screening_runs():
    r = frame_hash_duplicates(D / "videos" / "vid_002_duplicated_frames.mp4")
    assert r["duplicate_count"] >= 1


def test_image_deepfake_protocol_never_auto_verdicts():
    r = image_deepfake_protocol(D / "images" / "img_001_pristine.jpg")
    assert r["protocol_version"] == "MFLAB-DF-0.4"
    assert r["evidentiary_conclusion"] == "inconclusive"


def test_video_deepfake_protocol_never_auto_verdicts():
    r = video_deepfake_protocol(D / "videos" / "vid_001_pristine.mp4")
    assert r["protocol_version"] == "MFLAB-DF-0.4"
    assert r["evidentiary_conclusion"] == "inconclusive"


def test_external_model_requires_explicit_validation(tmp_path):
    p = tmp_path / "scores.json"
    p.write_text(json.dumps({"models": [
        {"name": "modelA", "score": 0.9, "validated": False},
        {"name": "modelB", "score": 0.8, "validated": True, "dataset": "documented"},
    ]}), encoding="utf-8")
    rows = load_exported_results(p)
    assert rows[0]["validated"] is False
    assert rows[1]["validated"] is True


def test_full_pipeline_writes_deepfake_protocol(tmp_path):
    p = D / "images" / "img_001_pristine.jpg"
    r = analyze_file(p, tmp_path, profile="deepfake")
    assert "c2pa" in r["methods"]
    assert "deepfake_protocol" in r["methods"]
    assert r["methods"]["deepfake_protocol"]["evidentiary_conclusion"] == "inconclusive"


def test_opencv_reads_non_ascii_path(tmp_path):
    """Regression for Windows evidence paths such as 'Perícia Digital'."""
    from shutil import copy2
    accented = tmp_path / "Perícia Digital"
    accented.mkdir()
    src = D / "images" / "img_001_pristine.jpg"
    dst = accented / "evidência_001.jpg"
    copy2(src, dst)
    r = histogram_analysis(dst)
    assert set(r["channels"]) == {"R", "G", "B"}


def test_windows_haar_cascade_recovers_from_mojibake_path():
    """The built-in cascade must still load if cv2.data returns a mangled path."""
    import os
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
    assert "face_boundary_texture_discontinuity" in r.get("screening_flags", [])
