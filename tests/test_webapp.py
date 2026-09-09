from __future__ import annotations

import io
import json
from pathlib import Path

from PIL import Image

import mf_lab.webapp as webapp
from mf_lab.version import current_version


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (120, 80, 40)).save(buf, format="PNG")
    return buf.getvalue()


def test_web_index_and_health(monkeypatch, tmp_path):
    monkeypatch.setattr(webapp, "RUN_ROOT", tmp_path)
    app = webapp.create_app()
    client = app.test_client()
    assert client.get("/").status_code == 200
    health = client.get("/api/health").get_json()
    assert health["status"] == "ok"
    assert health["version"] == current_version()


def test_multi_image_upload_and_download_links(monkeypatch, tmp_path):
    monkeypatch.setattr(webapp, "RUN_ROOT", tmp_path)

    def fake_analyze_case(case_dir, profile="full", run_veritas=False):
        case_dir = Path(case_dir)
        reports = []
        for p in sorted((case_dir / "original").iterdir()):
            reports.append({
                "file": str(p), "sha256": "a" * 64, "size_bytes": p.stat().st_size,
                "analyzed_at": "2026-09-08T00:00:00+00:00", "profile": profile,
                "methods": {
                    "copy_move_orb": {"suspicious_cluster_count": 1, "suspicious_pairs": 12, "score": .6},
                    "deepfake_protocol": {"triage_assessment": "screening_observations_only", "evidentiary_conclusion": "inconclusive", "screening_observations": []},
                },
            })
        (case_dir / "report.json").write_text(json.dumps({"reports": reports}), encoding="utf-8")
        return reports

    def fake_report(case_dir, fmt="docx"):
        final = Path(case_dir) / "final"; final.mkdir(exist_ok=True)
        p = final / (Path(case_dir).name + ("_laudo_preliminar.docx" if fmt == "docx" else "_laudo_preliminar.md"))
        p.write_bytes(b"test" if fmt == "docx" else b"# test")
        return str(p)

    monkeypatch.setattr(webapp, "analyze_case", fake_analyze_case)
    monkeypatch.setattr(webapp, "generate_preliminary_report", fake_report)
    app = webapp.create_app(); client = app.test_client()
    data = {"profile": "full", "files": [(io.BytesIO(_png_bytes()), "a.png"), (io.BytesIO(_png_bytes()), "b.png")]}
    response = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["files"] == 2
    assert payload["summary"]["screening_signals"] == 2
    assert payload["downloads"]["docx"].endswith("/download/docx")
    assert len(payload["files"]) == 2
