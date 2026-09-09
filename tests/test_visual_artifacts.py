from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from PIL import Image

from mf_lab.analysis.classical import frequency_analysis, histogram_analysis
from mf_lab.analysis.image import ela
from mf_lab.analysis.synthetic_features import extract_synthetic_feature_bank
from mf_lab.report.generator import generate_preliminary_report
from mf_lab.visual_artifacts import generate_visual_artifacts


def _image(path: Path) -> None:
    im = Image.new("RGB", (128, 96))
    px = im.load()
    for y in range(96):
        for x in range(128):
            px[x, y] = ((x * 2) % 256, (y * 3) % 256, (x + y) % 256)
    im.save(path, quality=92)


def test_visual_renderer_creates_expected_image_artifacts(tmp_path):
    media = tmp_path / "questioned.jpg"
    _image(media)
    methods = {
        "ela": ela(media),
        "histogram": histogram_analysis(media),
        "frequency": frequency_analysis(media),
        "synthetic_feature_bank": extract_synthetic_feature_bank(media),
    }
    result = generate_visual_artifacts(media, tmp_path, methods)
    assert result["status"] == "success"
    assert result["artifact_count"] >= 5
    ids = {x["id"] for x in result["items"]}
    assert {"ela", "noise_residual", "fft_spectrum", "rgb_histogram", "synthetic_feature_profile"} <= ids
    for row in result["items"]:
        assert (tmp_path / row["path"]).is_file()
        assert row["caption"]


def test_docx_report_contains_visual_appendix(tmp_path):
    case = tmp_path / "case-visual"
    for sub in ("original", "results", "final", "visuals"):
        (case / sub).mkdir(parents=True, exist_ok=True)
    media = case / "original" / "questioned.jpg"
    _image(media)
    visual = case / "visuals" / "questioned.jpg" / "fft_spectrum.png"
    visual.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 80), (20, 30, 40)).save(visual)
    (case / "case.yaml").write_text(
        "case:\n  id: case-visual\n  title: Teste visual\n  process_number: ''\n  court: ''\n  expert:\n    name: '[NOME DO PERITO]'\n    qualification: '[QUALIFICAÇÃO]'\n  scope: Teste.\n  questions: []\n",
        encoding="utf-8",
    )
    report = {
        "file": str(media),
        "sha256": "a" * 64,
        "methods": {"hash_sha256": {"sha256": "a" * 64}},
        "method_registry": {"hash_sha256": {"refs": []}},
        "visual_artifacts": {
            "status": "success",
            "artifact_count": 1,
            "items": [{
                "id": "fft_spectrum",
                "label": "Espectro FFT",
                "method": "frequency",
                "category": "frequencia",
                "path": "visuals/questioned.jpg/fft_spectrum.png",
                "caption": "Magnitude logarítmica do espectro.",
                "warning": "Triagem visual.",
            }],
        },
    }
    (case / "report.json").write_text(json.dumps({"reports": [report]}), encoding="utf-8")
    out = Path(generate_preliminary_report(case, "docx"))
    assert out.is_file()
    doc = Document(out)
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "APÊNDICE A" in text
    assert "Espectro FFT" in text
    assert len(doc.inline_shapes) >= 1
