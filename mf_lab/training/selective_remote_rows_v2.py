from __future__ import annotations

import csv
import json
from pathlib import Path

from . import selective_acquisition as sa
from .coco_paths import coco_http_url
from .selective_remote_rows import build_selective_plan_rows as _build_selective_plan_rows


def normalize_coco_sources(plan_csv: str | Path) -> dict:
    """Canonicalize COCO source URLs in an already-built selective plan.

    AI-GenBench's official real lists contain compact numeric COCO IDs. This
    normalization keeps the official file_id untouched while ensuring transport
    URLs use the zero-padded COCO 2017 filename. It is deliberately idempotent.
    """
    path = Path(plan_csv)
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    changed = 0
    for row in rows:
        file_id = str(row.get("file_id") or "")
        if file_id.startswith(("COCO2017_train/", "COCO2017_val/")):
            canonical = coco_http_url(file_id)
            if row.get("source_url") != canonical:
                row["source_url"] = canonical
                changed += 1
            row["source_kind"] = "coco"
            if not row.get("acquisition_status"):
                row["acquisition_status"] = "planned"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sa.REMOTE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return {"rows": len(rows), "coco_urls_normalized": changed}


def build_selective_plan_rows(*args, **kwargs) -> dict:
    """Build the base 52k plan and normalize all COCO transports canonically."""
    out_csv = args[0] if args else kwargs.get("out_csv")
    if out_csv is None:
        raise TypeError("out_csv is required")
    summary = _build_selective_plan_rows(*args, **kwargs)
    normalization = normalize_coco_sources(out_csv)
    summary = dict(summary)
    summary["coco_transport"] = {
        "id_policy": "official_aigenbench_file_id_preserved",
        "filename_policy": "zero_padded_12_digit_coco2017_jpeg",
        "transport": "official_http_endpoint",
        **normalization,
    }
    summary_path = Path(str(out_csv) + ".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
