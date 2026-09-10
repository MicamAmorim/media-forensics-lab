from __future__ import annotations

import csv
import hashlib
import io
import zipfile

from PIL import Image

from mf_lab.training import selective_acquisition as sa
from mf_lab.training import stable_real_acquisition_v2 as stable_v2


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_stable_v2_materializes_compact_coco_id_from_canonical_zip_member(tmp_path):
    raw = _png_bytes()
    archive = tmp_path / "train2017.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("train2017/000000123456.jpg", raw)

    plan = tmp_path / "plan.csv"
    row = {
        "sample_id": "real:train:COCO2017_train/123456",
        "source_split": "train",
        "row_index": "-1",
        "label": "0",
        "role": "fit",
        "generator": "(Real)",
        "generator_release_date": "",
        "generator_status": "real",
        "origin_dataset": "COCO2017_train",
        "file_id": "COCO2017_train/123456",
        "sample_rank": "1",
        "source_url": "http://images.cocodataset.org/train2017/000000123456.jpg",
        "source_kind": "coco",
        "local_path": "",
        "sha256": "",
        "acquisition_status": "planned",
    }
    with plan.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sa.REMOTE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerow(row)

    out = tmp_path / "materialized.csv"
    summary = stable_v2.materialize_stable_plan(
        plan,
        tmp_path / "images",
        out,
        cache_dir=tmp_path / "cache",
        archive_paths={"COCO2017_train": archive},
    )
    assert summary["failed_or_unresolved"] == 0
    assert summary["coco_id_policy"] == "canonical_zero_padded_12_digit_jpeg"
    with out.open("r", newline="", encoding="utf-8") as handle:
        materialized = next(csv.DictReader(handle))
    assert materialized["acquisition_status"] == "downloaded_coco_archive"
    assert materialized["sha256"] == hashlib.sha256(raw).hexdigest()
    assert open(materialized["local_path"], "rb").read() == raw
