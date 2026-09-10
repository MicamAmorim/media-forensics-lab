from __future__ import annotations

import csv
import hashlib
import io

import pytest
from PIL import Image

from mf_lab.training import selective_acquisition as sa
from mf_lab.training.selective_embeddings import validate_materialized_manifest


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_image_src_accepts_nested_dataset_viewer_shape():
    payload = {"image": {"src": "https://datasets-server.huggingface.co/assets/x.png"}}
    assert sa._image_src(payload).endswith("/assets/x.png")


def test_real_url_resolver_preserves_official_ids():
    url, kind = sa.resolve_real_url("COCO2017_train/000000123456.jpg")
    assert kind == "coco"
    assert url == "https://images.cocodataset.org/train2017/000000123456.jpg"

    url, kind = sa.resolve_real_url(
        "LAION-400M/42", laion_index={"LAION-400M/42": "https://example.test/42.jpg"}
    )
    assert kind == "laion"
    assert url == "https://example.test/42.jpg"


def test_balanced_real_selection_is_deterministic_and_without_replacement():
    ids = [f"COCO2017_train/{i:012d}.jpg" for i in range(20)]
    ids += [f"COCO2017_val/{i:012d}.jpg" for i in range(20)]
    ids += [f"LAION-400M/{i}" for i in range(20)]
    first = sa._balanced_file_ids(ids, 30, seed=17, salt="x")
    second = sa._balanced_file_ids(ids, 30, seed=17, salt="x")
    assert first == second
    assert len(first) == len(set(first)) == 30
    prefixes = [x.split("/", 1)[0] for x in first]
    assert prefixes.count("COCO2017_train") == 10
    assert prefixes.count("COCO2017_val") == 10
    assert prefixes.count("LAION-400M") == 10


def _write_manifest(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sa.REMOTE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _planned_row(sample_id="sample:1", label="1", role="fit"):
    return {
        "sample_id": sample_id,
        "source_split": "train",
        "row_index": "1",
        "label": label,
        "role": role,
        "generator": "CycleGAN" if label == "1" else "(Real)",
        "generator_release_date": "2017-03-30" if label == "1" else "",
        "generator_status": "seen" if label == "1" else "real",
        "origin_dataset": "mock",
        "file_id": f"mock/{sample_id}",
        "sample_rank": "1",
        "source_url": "https://example.test/image.png",
        "source_kind": "test",
        "local_path": "",
        "sha256": "",
        "acquisition_status": "planned",
    }


def test_materialize_plan_preserves_downloaded_bytes_and_sha(monkeypatch, tmp_path):
    raw = _png_bytes()
    monkeypatch.setattr(sa, "_download_bytes", lambda url, **kwargs: raw)

    plan = tmp_path / "plan.csv"
    _write_manifest(plan, [_planned_row()])

    out = tmp_path / "materialized.csv"
    result = sa.materialize_plan(plan, tmp_path / "images", out)
    assert result["downloaded"] == 1
    with out.open("r", newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["acquisition_status"] == "downloaded"
    assert row["sha256"] == hashlib.sha256(raw).hexdigest()
    with open(row["local_path"], "rb") as handle:
        assert handle.read() == raw


def test_verified_manifest_rejects_missing_downloads(tmp_path):
    manifest = tmp_path / "incomplete.csv"
    _write_manifest(
        manifest,
        [_planned_row("synthetic", "1"), _planned_row("real", "0")],
    )
    with pytest.raises(ValueError, match="not training-ready"):
        validate_materialized_manifest(manifest)


def test_verified_manifest_accepts_complete_balanced_sample(tmp_path):
    raw = _png_bytes()
    rows = [_planned_row("synthetic", "1"), _planned_row("real", "0")]
    for i, row in enumerate(rows):
        path = tmp_path / f"{i}.png"
        path.write_bytes(raw)
        row["local_path"] = str(path)
        row["sha256"] = hashlib.sha256(raw).hexdigest()
        row["acquisition_status"] = "downloaded"
    manifest = tmp_path / "complete.csv"
    _write_manifest(manifest, rows)
    result = validate_materialized_manifest(manifest)
    assert result["complete"] is True
    assert result["roles"]["fit"] == {"real": 1, "synthetic": 1}
