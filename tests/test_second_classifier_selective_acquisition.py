from __future__ import annotations

import csv
import hashlib
import io

from PIL import Image

from mf_lab.training import selective_acquisition as sa


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


def test_materialize_plan_preserves_downloaded_bytes_and_sha(monkeypatch, tmp_path):
    raw = _png_bytes()
    monkeypatch.setattr(sa, "_download_bytes", lambda url, **kwargs: raw)

    plan = tmp_path / "plan.csv"
    rows = [
        {
            "sample_id": "sample:1",
            "source_split": "train",
            "row_index": "1",
            "label": "1",
            "role": "fit",
            "generator": "CycleGAN",
            "generator_release_date": "2017-03-30",
            "generator_status": "seen",
            "origin_dataset": "mock",
            "file_id": "mock/1",
            "sample_rank": "1",
            "source_url": "https://example.test/image.png",
            "source_kind": "test",
            "local_path": "",
            "sha256": "",
            "acquisition_status": "planned",
        }
    ]
    with plan.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sa.REMOTE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    out = tmp_path / "materialized.csv"
    result = sa.materialize_plan(plan, tmp_path / "images", out)
    assert result["downloaded"] == 1
    with out.open("r", newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["acquisition_status"] == "downloaded"
    assert row["sha256"] == hashlib.sha256(raw).hexdigest()
    materialized = tmp_path / row["local_path"] if not row["local_path"].startswith(str(tmp_path)) else None
    actual_path = row["local_path"]
    with open(actual_path, "rb") as handle:
        assert handle.read() == raw
