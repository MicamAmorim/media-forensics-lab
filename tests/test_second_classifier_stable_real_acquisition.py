from __future__ import annotations

import csv
import hashlib
import io
import json
import urllib.error
import zipfile

from PIL import Image

from mf_lab.training import selective_acquisition as sa
from mf_lab.training import stable_real_acquisition as stable


def _png_bytes(color=(10, 20, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, format="PNG")
    return buf.getvalue()


def _row(*, sample_id: str, label: int, role: str, kind: str, file_id: str, url: str):
    return {
        "sample_id": sample_id,
        "source_split": "train",
        "row_index": "-1",
        "label": str(label),
        "role": role,
        "generator": "CycleGAN" if label else "(Real)",
        "generator_release_date": "2017-03-30" if label else "",
        "generator_status": "seen" if label else "real",
        "origin_dataset": file_id.split("/", 1)[0],
        "file_id": file_id,
        "sample_rank": "1",
        "source_url": url,
        "source_kind": kind,
        "local_path": "",
        "sha256": "",
        "acquisition_status": "planned",
    }


def _write_manifest(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sa.REMOTE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_coco_archive_materializes_selected_original_bytes(tmp_path):
    raw = _png_bytes()
    archive = tmp_path / "train2017.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("train2017/000000123456.jpg", raw)

    row = _row(
        sample_id="real:train:COCO2017_train/000000123456.jpg",
        label=0,
        role="fit",
        kind="coco",
        file_id="COCO2017_train/000000123456.jpg",
        url="https://images.cocodataset.org/train2017/000000123456.jpg",
    )
    rows, diagnostics = stable.materialize_coco_archive_rows(
        [row],
        tmp_path / "images",
        tmp_path / "cache",
        archive_paths={"COCO2017_train": archive},
    )
    assert diagnostics == []
    assert rows[0]["acquisition_status"] == "downloaded_coco_archive"
    assert rows[0]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert open(rows[0]["local_path"], "rb").read() == raw


def test_laion_failed_url_uses_deterministic_audited_replacement(monkeypatch, tmp_path):
    raw = _png_bytes((40, 50, 60))
    plan = tmp_path / "plan.csv"
    row = _row(
        sample_id="real:train:LAION-400M/original",
        label=0,
        role="fit",
        kind="laion",
        file_id="LAION-400M/original",
        url="https://dead.example/original.jpg",
    )
    _write_manifest(plan, [row])

    monkeypatch.setattr(
        stable,
        "_laion_reserve",
        lambda *args, **kwargs: [("LAION-400M/replacement", "https://ok.example/replacement.jpg")],
    )

    def fake_download(url, **kwargs):
        if "dead.example" in url:
            return None, {
                **stable._diag_base(url),
                "attempts": 4,
                "http_status": 404,
                "exception_type": "HTTPError",
                "failure_reason": "Not Found",
            }
        return raw, {
            **stable._diag_base(url),
            "attempts": 1,
            "http_status": 200,
            "final_url": url,
        }

    monkeypatch.setattr(stable, "download_bytes_diagnostic", fake_download)
    out = tmp_path / "materialized.csv"
    replacement_log = tmp_path / "replacements.json"
    summary = stable.materialize_stable_plan(
        plan,
        tmp_path / "images",
        out,
        cache_dir=tmp_path / "cache",
        replacement_log_out=replacement_log,
    )
    assert summary["failed_or_unresolved"] == 0
    assert summary["replacements"] == 1
    with out.open("r", newline="", encoding="utf-8") as handle:
        materialized = next(csv.DictReader(handle))
    assert materialized["file_id"] == "LAION-400M/replacement"
    assert materialized["source_kind"] == "laion_replacement"
    assert materialized["acquisition_status"] == "downloaded_replacement"
    assert materialized["sha256"] == hashlib.sha256(raw).hexdigest()
    replacements = json.loads(replacement_log.read_text(encoding="utf-8"))
    assert replacements[0]["replacement_for"]["file_id"] == "LAION-400M/original"
    assert replacements[0]["replacement"]["file_id"] == "LAION-400M/replacement"


def test_http_diagnostics_preserve_status_and_reason(monkeypatch):
    def fail(*args, **kwargs):
        raise urllib.error.HTTPError(
            "https://example.test/x.jpg", 403, "Forbidden", hdrs=None, fp=None
        )

    monkeypatch.setattr(urllib.request, "urlopen", fail)
    raw, diag = stable.download_bytes_diagnostic(
        "https://example.test/x.jpg", retries=1
    )
    assert raw is None
    assert diag["http_status"] == 403
    assert diag["host"] == "example.test"
    assert diag["exception_type"] == "HTTPError"
    assert "Forbidden" in diag["failure_reason"]


def test_freeze_corpus_recomputes_hashes_and_emits_lock(tmp_path):
    raw_real = _png_bytes((1, 2, 3))
    raw_fake = _png_bytes((4, 5, 6))
    real_path = tmp_path / "real.png"
    fake_path = tmp_path / "fake.png"
    real_path.write_bytes(raw_real)
    fake_path.write_bytes(raw_fake)

    real = _row(
        sample_id="real:1",
        label=0,
        role="fit",
        kind="laion",
        file_id="LAION-400M/1",
        url="https://example.test/real.png",
    )
    fake = _row(
        sample_id="fake:1",
        label=1,
        role="fit",
        kind="hf_dataset_viewer",
        file_id="hf/1",
        url="https://example.test/fake.png",
    )
    for row, path, raw in ((real, real_path, raw_real), (fake, fake_path, raw_fake)):
        row["local_path"] = str(path)
        row["sha256"] = hashlib.sha256(raw).hexdigest()
        row["acquisition_status"] = "downloaded"

    manifest = tmp_path / "materialized.csv"
    _write_manifest(manifest, [real, fake])
    frozen = tmp_path / "frozen.csv"
    lock_path = tmp_path / "corpus.lock.json"
    lock = stable.freeze_materialized_corpus(manifest, frozen, lock_path)
    assert lock["rows"] == 2
    assert lock["all_sample_sha256_verified"] is True
    assert lock["corpus_id"].startswith("mflab-aigenbench-derived-v1-")
    assert lock["frozen_manifest_sha256"] == hashlib.sha256(frozen.read_bytes()).hexdigest()
    assert json.loads(lock_path.read_text(encoding="utf-8"))["corpus_id"] == lock["corpus_id"]
