from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from PIL import Image

from mf_lab.training import selective_acquisition as sa
from mf_lab.training.selective_embeddings import validate_materialized_manifest
from mf_lab.training.selective_remote_rows import fetch_generator_quota_rows
from mf_lab.training.stable_real_acquisition import (
    freeze_materialized_corpus,
    materialize_stable_plan,
)


def _pick_real(ids: list[str], prefix: str, count: int, *, offset: int = 0) -> list[str]:
    candidates = sorted(x for x in ids if x.startswith(prefix + "/"))
    selected = candidates[offset : offset + count]
    if len(selected) < count:
        raise RuntimeError(f"need {count} {prefix} controls, found {len(selected)}")
    return selected


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


def main() -> int:
    work = Path("work/second_classifier/remote-smoke")
    cache = work / "cache"
    images = work / "images"
    plan_path = work / "plan.csv"
    materialized_path = work / "materialized.csv"
    diagnostics_path = work / "diagnostics.json"
    replacements_path = work / "replacements.json"
    frozen_manifest = work / "frozen-manifest.csv"
    corpus_lock = work / "corpus.lock.json"
    report_path = work / "remote-smoke-report.json"
    work.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []

    # 50 synthetic images across old and modern generators. Dataset Viewer
    # filter/search indexes are intentionally avoided; deterministic /rows page
    # scanning supplies only the requested quota.
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

    # For the network smoke, real controls are LAION-only. COCO-via-official-ZIP
    # is covered by a deterministic archive test in pytest so an ephemeral CI
    # runner never downloads the ~18 GB train2017 archive merely to test logic.
    train_ids = sa.load_official_real_file_ids("train", cache_dir=cache)
    val_ids = sa.load_official_real_file_ids("validation", cache_dir=cache)
    laion_train = sa.load_laion_url_index("train", cache_dir=cache)
    laion_val = sa.load_laion_url_index("validation", cache_dir=cache)

    fit_real = _pick_real(train_ids, "LAION-400M", 20)
    iid_real = _pick_real(val_ids, "LAION-400M", 15)
    ood_real = _pick_real(val_ids, "LAION-400M", 15, offset=15)

    for rank, file_id in enumerate(fit_real, 1):
        url, kind = sa.resolve_real_url(file_id, laion_index=laion_train)
        row = sa._real_manifest_row(
            "train", file_id, "fit", source_url=url, source_kind=kind, rank=rank
        )
        rows.append(row)
    for file_id in iid_real:
        url, kind = sa.resolve_real_url(file_id, laion_index=laion_val)
        rows.append(sa._real_manifest_row(
            "validation", file_id, "iid_test", source_url=url, source_kind=kind
        ))
    for file_id in ood_real:
        url, kind = sa.resolve_real_url(file_id, laion_index=laion_val)
        rows.append(sa._real_manifest_row(
            "validation", file_id, "ood_test", source_url=url, source_kind=kind
        ))

    # Force exactly one deterministic dead original URL so the live smoke proves
    # the reserve/replacement mechanism rather than relying on naturally dead URLs.
    for row in rows:
        if row["label"] == 0 and row["role"] == "fit":
            row["source_url"] = "http://127.0.0.1:9/mflab-forced-dead-laion.jpg"
            break

    if len(rows) != 100:
        raise AssertionError(f"remote smoke must contain exactly 100 rows, got {len(rows)}")

    with plan_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sa.REMOTE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    acquisition = materialize_stable_plan(
        plan_path,
        images,
        materialized_path,
        cache_dir=cache,
        diagnostics_out=diagnostics_path,
        replacement_log_out=replacements_path,
        seed=sa.DEFAULT_SEED,
    )

    verification = None
    verification_error = None
    try:
        verification = validate_materialized_manifest(materialized_path)
    except Exception as exc:
        verification_error = f"{type(exc).__name__}: {exc}"

    lock = None
    if verification is not None:
        lock = freeze_materialized_corpus(
            materialized_path,
            frozen_manifest,
            corpus_lock,
            replacement_log=replacements_path,
        )

    with materialized_path.open("r", newline="", encoding="utf-8") as handle:
        materialized = list(csv.DictReader(handle))
    replacements = json.loads(replacements_path.read_text(encoding="utf-8"))
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))

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
        and acquisition["replacements"] >= 1
        and verification is not None
        and verification.get("complete") is True
        and verification.get("all_sha256_verified") is True
        and lock is not None
        and lock.get("all_sample_sha256_verified") is True
        and sha_postcheck_failures == 0
    )
    report = {
        "protocol": "MFLAB-SCI-AIGENBENCH-SECOND-REMOTE-SMOKE-0.5",
        "remote_backend": "dataset_viewer_rows_random_page_scan",
        "real_smoke_strategy": "laion_with_forced_audited_replacement",
        "coco_validation_strategy": "pytest_local_zip_fixture; full acquisition uses official COCO ZIP archives",
        "rows": len(materialized),
        "scan": {"train": train_scan, "validation": val_scan},
        "acquisition": acquisition,
        "verification": verification,
        "verification_error": verification_error,
        "replacement_count": len(replacements),
        "diagnostic_records": len(diagnostics),
        "role_class_counts": {
            f"{role}:{'synthetic' if label == '1' else 'real'}": count
            for (role, label), count in sorted(role_counts.items())
        },
        "image_format_counts": dict(format_counts),
        "bytes_verified": int(total_bytes),
        "sha_postcheck_failures": int(sha_postcheck_failures),
        "corpus_lock": lock,
        "success": bool(success),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
