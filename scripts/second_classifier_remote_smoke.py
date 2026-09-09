from __future__ import annotations

import csv
import hashlib
import json
import urllib.parse
from collections import Counter
from pathlib import Path

from PIL import Image

from mf_lab.training import selective_acquisition as sa
from mf_lab.training.selective_embeddings import validate_materialized_manifest
from mf_lab.training.selective_remote_rows import fetch_generator_quota_rows


def _pick_real(ids: list[str], prefix: str, count: int) -> list[str]:
    candidates = sorted(x for x in ids if x.startswith(prefix + "/"))
    if len(candidates) < count:
        raise RuntimeError(f"need {count} {prefix} controls, found {len(candidates)}")
    return candidates[:count]


def _image_info(path: str) -> dict:
    p = Path(path)
    raw = p.read_bytes()
    with Image.open(p) as img:
        return {
            "format": str(img.format or "unknown"),
            "width": int(img.width),
            "height": int(img.height),
            "bytes": int(len(raw)),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }


def _base_source_kind(row: dict) -> str:
    return str(row.get("source_kind") or "unknown").split(";", 1)[0]


def _host(row: dict) -> str:
    return urllib.parse.urlparse(str(row.get("source_url") or "")).netloc or "(none)"


def main() -> int:
    work = Path("work/second_classifier/remote-smoke")
    cache = work / "cache"
    images = work / "images"
    plan_path = work / "plan.csv"
    materialized_path = work / "materialized.csv"
    report_path = work / "remote-smoke-report.json"
    work.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []

    # 50 synthetic images collected from deterministic random pages across the
    # split, avoiding Dataset Viewer filter/search indexes that time out on this
    # 35 GB image dataset.
    train_selected, train_scan = fetch_generator_quota_rows(
        "train", {"CycleGAN": 20}, cache_dir=cache, seed=sa.DEFAULT_SEED
    )
    val_selected, val_scan = fetch_generator_quota_rows(
        "validation",
        {"DALL-E 3": 15, "FLUX 1 Schnell": 15},
        cache_dir=cache,
        seed=sa.DEFAULT_SEED,
    )

    for rank, row in enumerate(train_selected["CycleGAN"], 1):
        rows.append(sa._fake_manifest_row(row, "fit", "seen", rank))
    for rank, row in enumerate(val_selected["DALL-E 3"], 1):
        rows.append(sa._fake_manifest_row(row, "iid_test", "ood-smoke", rank))
    for rank, row in enumerate(val_selected["FLUX 1 Schnell"], 1):
        rows.append(sa._fake_manifest_row(row, "ood_test", "ood", rank))

    # 50 official real controls: COCO on both benchmark splits plus LAION on
    # validation. These IDs come from AI-GenBench's published real-file lists.
    train_ids = sa.load_official_real_file_ids("train", cache_dir=cache)
    val_ids = sa.load_official_real_file_ids("validation", cache_dir=cache)
    laion_val = sa.load_laion_url_index("validation", cache_dir=cache)

    for rank, file_id in enumerate(_pick_real(train_ids, "COCO2017_train", 20), 1):
        url, kind = sa.resolve_real_url(file_id)
        rows.append(
            sa._real_manifest_row(
                "train", file_id, "fit", source_url=url, source_kind=kind, rank=rank
            )
        )
    for file_id in _pick_real(val_ids, "COCO2017_val", 15):
        url, kind = sa.resolve_real_url(file_id)
        rows.append(
            sa._real_manifest_row(
                "validation", file_id, "iid_test", source_url=url, source_kind=kind
            )
        )
    for file_id in _pick_real(val_ids, "LAION-400M", 15):
        url, kind = sa.resolve_real_url(file_id, laion_index=laion_val)
        if not url:
            raise RuntimeError(f"official LAION ID missing from URL index: {file_id}")
        rows.append(
            sa._real_manifest_row(
                "validation", file_id, "ood_test", source_url=url, source_kind=kind
            )
        )

    if len(rows) != 100:
        raise AssertionError(f"remote smoke must contain exactly 100 rows, got {len(rows)}")

    with plan_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sa.REMOTE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    acquisition = sa.materialize_plan(plan_path, images, materialized_path)
    with materialized_path.open("r", newline="", encoding="utf-8") as handle:
        materialized = list(csv.DictReader(handle))

    failed_rows = [
        row
        for row in materialized
        if row.get("acquisition_status") not in {"downloaded", "cached"}
        or not row.get("local_path")
    ]
    failure_diag = {
        "count": len(failed_rows),
        "by_source_kind": dict(Counter(_base_source_kind(row) for row in failed_rows)),
        "by_generator": dict(Counter(str(row.get("generator") or "") for row in failed_rows)),
        "by_host": dict(Counter(_host(row) for row in failed_rows)),
        "by_role": dict(Counter(str(row.get("role") or "") for row in failed_rows)),
        "by_status": dict(Counter(str(row.get("acquisition_status") or "") for row in failed_rows)),
        "examples": [
            {
                "sample_id": row.get("sample_id"),
                "source_kind": row.get("source_kind"),
                "generator": row.get("generator"),
                "role": row.get("role"),
                "host": _host(row),
                "status": row.get("acquisition_status"),
            }
            for row in failed_rows[:20]
        ],
    }

    verification = None
    verification_error = None
    try:
        verification = validate_materialized_manifest(materialized_path)
    except Exception as exc:
        verification_error = f"{type(exc).__name__}: {exc}"

    source_counts = Counter(_base_source_kind(row) for row in materialized)
    role_counts = Counter((row["role"], row["label"]) for row in materialized)
    format_counts: Counter[str] = Counter()
    total_bytes = 0
    sha_postcheck_failures = 0
    for row in materialized:
        local_path = str(row.get("local_path") or "")
        if not local_path or not Path(local_path).is_file():
            continue
        info = _image_info(local_path)
        if not row.get("sha256") or info["sha256"].lower() != row["sha256"].lower():
            sha_postcheck_failures += 1
        format_counts[info["format"]] += 1
        total_bytes += info["bytes"]

    success = (
        acquisition["failed_or_unresolved"] == 0
        and verification is not None
        and verification.get("complete") is True
        and verification.get("all_sha256_verified") is True
        and sha_postcheck_failures == 0
    )
    report = {
        "protocol": "MFLAB-SCI-AIGENBENCH-SECOND-REMOTE-SMOKE-0.4",
        "remote_backend": "dataset_viewer_rows_random_page_scan",
        "rows": len(materialized),
        "scan": {"train": train_scan, "validation": val_scan},
        "acquisition": acquisition,
        "verification": verification,
        "verification_error": verification_error,
        "failure_diagnostics": failure_diag,
        "source_kind_counts": dict(source_counts),
        "role_class_counts": {
            f"{role}:{'synthetic' if label == '1' else 'real'}": count
            for (role, label), count in sorted(role_counts.items())
        },
        "image_format_counts": dict(format_counts),
        "bytes_verified": int(total_bytes),
        "sha_postcheck_failures": int(sha_postcheck_failures),
        "success": bool(success),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
