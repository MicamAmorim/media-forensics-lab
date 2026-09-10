from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

from PIL import Image

from mf_lab.training import selective_acquisition as sa
from mf_lab.training.coco_paths import canonical_coco_filename, coco_http_url
from mf_lab.training.stable_real_acquisition import download_bytes_diagnostic


def _pick(ids: list[str], prefix: str, n: int) -> list[str]:
    rows = [x for x in ids if x.startswith(prefix + "/")]
    if len(rows) < n:
        raise RuntimeError(f"need {n} {prefix} ids, found {len(rows)}")
    return rows[:n]


def main() -> int:
    work = Path("work/second_classifier/coco-live-smoke")
    cache = work / "cache"
    work.mkdir(parents=True, exist_ok=True)

    train_ids = sa.load_official_real_file_ids("train", cache_dir=cache)
    validation_ids = sa.load_official_real_file_ids("validation", cache_dir=cache)
    selected = (
        _pick(train_ids, "COCO2017_train", 3)
        + _pick(train_ids, "COCO2017_val", 3)
        + _pick(validation_ids, "COCO2017_train", 2)
        + _pick(validation_ids, "COCO2017_val", 2)
    )

    records = []
    for file_id in selected:
        url = coco_http_url(file_id)
        raw, diag = download_bytes_diagnostic(url, timeout=60, retries=3)
        record = {
            "file_id": file_id,
            "canonical_filename": canonical_coco_filename(file_id),
            "url": url,
            "diagnostic": diag,
            "decode_ok": False,
            "sha256": "",
            "bytes": 0,
        }
        if raw is not None:
            try:
                with Image.open(io.BytesIO(raw)) as img:
                    img.verify()
                record["decode_ok"] = True
                record["sha256"] = hashlib.sha256(raw).hexdigest()
                record["bytes"] = len(raw)
            except Exception as exc:
                record["decode_error"] = f"{type(exc).__name__}: {exc}"
        records.append(record)

    success = len(records) == 10 and all(
        r["decode_ok"] and len(r["sha256"]) == 64 and r["bytes"] > 0
        for r in records
    )
    report = {
        "protocol": "MFLAB-SCI-COCO-DIRECT-LIVE-SMOKE-0.1",
        "purpose": "verify canonical reconstruction of compact AI-GenBench COCO ids",
        "rows": len(records),
        "success": success,
        "records": records,
    }
    out = work / "report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
