from __future__ import annotations

import csv
import hashlib
import json
import shutil
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Sequence

import numpy as np

from . import selective_acquisition as sa
from .coco_paths import coco_http_url
from .second_classifier import DEFAULT_BACKBONE, DEFAULT_SEED, _stable_seed
from .selective_remote_rows import _parse_viewer_row, _rows_json_get, _rows_url
from .stable_real_acquisition import _diag_base, _write_row_bytes, download_bytes_diagnostic

SHARD_PROTOCOL = "MFLAB-SCI-AIGENBENCH-DERIVED-SHARD-0.1"
MERGE_PROTOCOL = "MFLAB-SCI-AIGENBENCH-DERIVED-EMBEDDING-MERGE-0.1"


def _stable_mod(value: str, modulus: int) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % modulus


def shard_index_for_row(row: dict, num_shards: int, *, page_size: int = 100) -> int:
    """Assign rows reproducibly while co-locating synthetic Dataset Viewer pages.

    All selected synthetic rows from the same `/rows` page are sent to one
    shard. This makes a fresh signed image URL page necessary only once per
    shard instead of once per selected image. Real controls are distributed by
    stable sample-id hashing.
    """
    if num_shards <= 0:
        raise ValueError("num_shards must be > 0")
    if int(row["label"]) == 1:
        split = str(row["source_split"])
        page = int(row["row_index"]) // page_size
        key = f"hf-page:{split}:{page}"
    else:
        key = f"real:{row['sample_id']}"
    return _stable_mod(key, num_shards)


def load_plan(path: str | Path) -> list[dict]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("second-classifier plan is empty")
    ids = [str(r["sample_id"]) for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("second-classifier plan contains duplicate sample IDs")
    return rows


def select_shard_rows(
    rows: Sequence[dict], shard_index: int, num_shards: int, *, page_size: int = 100
) -> list[dict]:
    if not 0 <= shard_index < num_shards:
        raise ValueError(f"shard_index must be in [0,{num_shards})")
    return [
        dict(row)
        for row in rows
        if shard_index_for_row(row, num_shards, page_size=page_size) == shard_index
    ]


def refresh_synthetic_urls(
    rows: Sequence[dict], *, page_size: int = 100, request_delay_seconds: float = 0.5
) -> dict:
    """Refresh expiring HF cached-asset URLs immediately before acquisition."""
    grouped: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows:
        if int(row["label"]) != 1:
            continue
        split = str(row["source_split"])
        page_offset = (int(row["row_index"]) // page_size) * page_size
        grouped[(split, page_offset)].append(row)

    requests = 0
    rate_limit_hits = 0
    refreshed = 0
    for (split, offset), page_rows in sorted(grouped.items()):
        length = min(page_size, (144_000 if split == "train" else 36_000) - offset)
        payload, meta = _rows_json_get(_rows_url(split, offset, length))
        requests += 1
        rate_limit_hits += int(meta.get("rate_limit_hits", 0))
        page_map: dict[int, dict] = {}
        for item in payload.get("rows") or []:
            parsed = _parse_viewer_row(item, split)
            page_map[int(parsed["row_index"])] = parsed
        for row in page_rows:
            idx = int(row["row_index"])
            parsed = page_map.get(idx)
            if parsed is None or not parsed.get("source_url"):
                raise RuntimeError(f"could not refresh synthetic URL for {split}:{idx}")
            if str(parsed["generator"]) != str(row["generator"]):
                raise RuntimeError(
                    f"generator changed while refreshing {split}:{idx}: "
                    f"plan={row['generator']} remote={parsed['generator']}"
                )
            row["source_url"] = str(parsed["source_url"])
            refreshed += 1
        if request_delay_seconds > 0:
            time.sleep(float(request_delay_seconds))
    return {
        "synthetic_rows_refreshed": refreshed,
        "dataset_viewer_page_requests": requests,
        "rate_limit_hits": rate_limit_hits,
        "page_size": page_size,
    }


def _all_planned_laion_ids(plan_rows: Sequence[dict], split: str) -> set[str]:
    return {
        str(row["file_id"])
        for row in plan_rows
        if int(row["label"]) == 0
        and str(row["source_split"]) == split
        and str(row["file_id"]).startswith("LAION-400M/")
    }


def _laion_reserve_for_shard(
    plan_rows: Sequence[dict],
    split: str,
    *,
    cache_dir: str | Path,
    seed: int,
    shard_index: int,
    num_shards: int,
) -> list[tuple[str, str]]:
    planned = _all_planned_laion_ids(plan_rows, split)
    official = sa.load_official_real_file_ids(split, cache_dir=cache_dir)
    index = sa.load_laion_url_index(split, cache_dir=cache_dir)
    candidates = [
        file_id
        for file_id in official
        if file_id.startswith("LAION-400M/")
        and file_id not in planned
        and index.get(file_id)
    ]
    rng = np.random.default_rng(_stable_seed(seed, "sharded-laion-reserve", split))
    order = [candidates[int(i)] for i in rng.permutation(len(candidates))]
    # Disjoint reserve pools across shards guarantee that independent jobs can
    # never choose the same replacement image.
    assigned = [
        file_id
        for pos, file_id in enumerate(order)
        if pos % num_shards == shard_index
    ]
    return [(file_id, index[file_id]) for file_id in assigned]


def _download_one(row: dict) -> tuple[bytes | None, dict]:
    file_id = str(row.get("file_id") or "")
    if str(row.get("source_kind") or "") == "coco" or file_id.startswith(
        ("COCO2017_train/", "COCO2017_val/")
    ):
        url = coco_http_url(file_id)
        row["source_url"] = url
        row["source_kind"] = "coco"
    else:
        url = str(row.get("source_url") or "")
    if not url:
        return None, {**_diag_base(url), "failure_reason": "unresolved source URL"}
    return download_bytes_diagnostic(url, timeout=90, retries=4)


def _validate_shard_materialization(rows: Sequence[dict]) -> dict:
    missing: list[str] = []
    mismatch: list[str] = []
    for row in rows:
        path = Path(str(row.get("local_path") or ""))
        digest = str(row.get("sha256") or "")
        if not path.is_file() or len(digest) != 64:
            missing.append(str(row.get("sample_id")))
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual.lower() != digest.lower():
            mismatch.append(str(row.get("sample_id")))
    if missing or mismatch:
        raise ValueError(
            f"shard materialization incomplete: missing={len(missing)} sha_mismatch={len(mismatch)}"
        )
    return {
        "rows": len(rows),
        "complete": True,
        "all_sha256_verified": True,
    }


def materialize_shard(
    plan_csv: str | Path,
    output_dir: str | Path,
    materialized_csv: str | Path,
    *,
    cache_dir: str | Path,
    shard_index: int,
    num_shards: int,
    workers: int = 8,
    seed: int = DEFAULT_SEED,
    page_size: int = 100,
    diagnostics_out: str | Path | None = None,
    replacements_out: str | Path | None = None,
) -> dict:
    plan_rows = load_plan(plan_csv)
    rows = select_shard_rows(plan_rows, shard_index, num_shards, page_size=page_size)
    if not rows:
        raise ValueError(f"shard {shard_index}/{num_shards} contains no rows")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    refresh = refresh_synthetic_urls(rows, page_size=page_size)
    diagnostics: list[dict] = []
    replacements: list[dict] = []
    failed_laion: list[dict] = []
    hard_failures: list[dict] = []

    # Initial source downloads can run concurrently; final row ordering and
    # replacement selection remain deterministic.
    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        futures = {pool.submit(_download_one, row): pos for pos, row in enumerate(rows)}
        results: dict[int, tuple[bytes | None, dict]] = {}
        for future in as_completed(futures):
            pos = futures[future]
            results[pos] = future.result()

    for pos, row in enumerate(rows):
        raw, diag = results[pos]
        diagnostics.append(
            {
                "kind": "initial",
                "sample_id": row["sample_id"],
                "file_id": row["file_id"],
                "source_kind": row.get("source_kind"),
                **diag,
            }
        )
        if raw is not None:
            try:
                _write_row_bytes(row, raw, root, "downloaded")
                continue
            except Exception as exc:
                diagnostics.append(
                    {
                        "kind": "decode",
                        "sample_id": row["sample_id"],
                        "file_id": row["file_id"],
                        "exception_type": type(exc).__name__,
                        "failure_reason": str(exc),
                    }
                )
        if str(row.get("file_id") or "").startswith("LAION-400M/"):
            failed_laion.append(row)
        else:
            hard_failures.append(row)

    reserve_by_split: dict[str, list[tuple[str, str]]] = {}
    reserve_pos: dict[str, int] = {}
    for split in sorted({str(r["source_split"]) for r in failed_laion}):
        reserve_by_split[split] = _laion_reserve_for_shard(
            plan_rows,
            split,
            cache_dir=cache_dir,
            seed=seed,
            shard_index=shard_index,
            num_shards=num_shards,
        )
        reserve_pos[split] = 0

    # Failed originals are handled in stable sample-id order. Concurrency above
    # therefore cannot change which reserve image fills which planned slot.
    for row in sorted(failed_laion, key=lambda r: str(r["sample_id"])):
        split = str(row["source_split"])
        reserve = reserve_by_split[split]
        original_file_id = str(row["file_id"])
        original_url = str(row.get("source_url") or "")
        success = False
        while reserve_pos[split] < len(reserve):
            candidate_file_id, candidate_url = reserve[reserve_pos[split]]
            reserve_pos[split] += 1
            raw, diag = download_bytes_diagnostic(candidate_url, timeout=90, retries=3)
            diagnostics.append(
                {
                    "kind": "laion_replacement_attempt",
                    "sample_id": row["sample_id"],
                    "replacement_file_id": candidate_file_id,
                    **diag,
                }
            )
            if raw is None:
                continue
            try:
                candidate = dict(row)
                candidate["file_id"] = candidate_file_id
                candidate["source_url"] = candidate_url
                candidate["source_kind"] = "laion_replacement"
                # sample_id intentionally stays the planned slot identity.
                _write_row_bytes(candidate, raw, root, "downloaded_replacement")
            except Exception as exc:
                diagnostics.append(
                    {
                        "kind": "laion_replacement_decode",
                        "sample_id": row["sample_id"],
                        "replacement_file_id": candidate_file_id,
                        "exception_type": type(exc).__name__,
                        "failure_reason": str(exc),
                    }
                )
                continue
            row.clear()
            row.update(candidate)
            replacements.append(
                {
                    "sample_id": row["sample_id"],
                    "original_file_id": original_file_id,
                    "original_url": original_url,
                    "replacement_file_id": candidate_file_id,
                    "replacement_url": candidate_url,
                    "replacement_sha256": row["sha256"],
                }
            )
            success = True
            break
        if not success:
            hard_failures.append(row)

    if hard_failures:
        for row in hard_failures:
            row["acquisition_status"] = "failed"
            row["local_path"] = ""
            row["sha256"] = ""

    out = Path(materialized_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sa.REMOTE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    diag_path = Path(diagnostics_out) if diagnostics_out else out.with_suffix(out.suffix + ".diagnostics.json")
    repl_path = Path(replacements_out) if replacements_out else out.with_suffix(out.suffix + ".replacements.json")
    diag_path.write_text(json.dumps(diagnostics, indent=2, ensure_ascii=False), encoding="utf-8")
    repl_path.write_text(json.dumps(replacements, indent=2, ensure_ascii=False), encoding="utf-8")

    if hard_failures:
        raise RuntimeError(
            f"shard {shard_index}/{num_shards} has {len(hard_failures)} unrecoverable downloads"
        )
    verification = _validate_shard_materialization(rows)
    role_counts = Counter(f"{r['role']}:{r['label']}" for r in rows)
    source_counts = Counter(str(r.get("source_kind") or "") for r in rows)
    return {
        "protocol": SHARD_PROTOCOL,
        "shard_index": int(shard_index),
        "num_shards": int(num_shards),
        "rows": len(rows),
        "workers": int(workers),
        "refresh": refresh,
        "verification": verification,
        "replacements": len(replacements),
        "role_label_counts": dict(role_counts),
        "source_kind_counts": dict(source_counts),
        "diagnostics": str(diag_path),
        "replacement_log": str(repl_path),
    }


def embed_materialized_shard(
    materialized_csv: str | Path,
    out_npz: str | Path,
    *,
    backbone: str = DEFAULT_BACKBONE,
    batch_size: int = 32,
    device: str = "auto",
) -> dict:
    from .selective_acquisition import extract_materialized_embeddings

    verification = _validate_shard_materialization(load_plan(materialized_csv))
    metadata = extract_materialized_embeddings(
        materialized_csv,
        out_npz,
        backbone=backbone,
        batch_size=batch_size,
        device=device,
    )
    return {**metadata, "shard_verification": verification}


def acquire_and_embed_shard(
    plan_csv: str | Path,
    work_dir: str | Path,
    *,
    shard_index: int,
    num_shards: int,
    cache_dir: str | Path,
    workers: int = 8,
    backbone: str = DEFAULT_BACKBONE,
    batch_size: int = 32,
    device: str = "auto",
    delete_raw_after_embedding: bool = True,
) -> dict:
    root = Path(work_dir)
    images = root / "images"
    materialized = root / "materialized.csv"
    embeddings = root / f"embeddings-shard-{shard_index:02d}.npz"
    acquisition = materialize_shard(
        plan_csv,
        images,
        materialized,
        cache_dir=cache_dir,
        shard_index=shard_index,
        num_shards=num_shards,
        workers=workers,
        diagnostics_out=root / "diagnostics.json",
        replacements_out=root / "replacements.json",
    )
    embedding = embed_materialized_shard(
        materialized,
        embeddings,
        backbone=backbone,
        batch_size=batch_size,
        device=device,
    )
    raw_deleted = False
    if delete_raw_after_embedding and images.exists():
        shutil.rmtree(images)
        raw_deleted = True
    report = {
        "protocol": SHARD_PROTOCOL,
        "shard_index": shard_index,
        "num_shards": num_shards,
        "acquisition": acquisition,
        "embedding": embedding,
        "embedding_path": str(embeddings),
        "materialized_manifest": str(materialized),
        "raw_deleted_after_embedding": raw_deleted,
        "success": True,
    }
    (root / "shard-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def merge_embedding_shards(
    plan_csv: str | Path,
    shard_npz_paths: Sequence[str | Path],
    out_npz: str | Path,
) -> dict:
    plan_rows = load_plan(plan_csv)
    plan_ids = [str(row["sample_id"]) for row in plan_rows]
    plan_pos = {sample_id: i for i, sample_id in enumerate(plan_ids)}

    pieces: list[dict[str, np.ndarray]] = []
    for path in shard_npz_paths:
        data = np.load(path, allow_pickle=False)
        pieces.append(
            {
                key: data[key]
                for key in ("X", "y", "role", "generator", "origin_dataset", "sample_id", "sample_rank")
            }
        )
    merged = {key: np.concatenate([p[key] for p in pieces], axis=0) for key in pieces[0]}
    ids = [str(x) for x in merged["sample_id"].tolist()]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate sample ids across embedding shards")
    if set(ids) != set(plan_ids):
        missing = len(set(plan_ids) - set(ids))
        extra = len(set(ids) - set(plan_ids))
        raise ValueError(f"embedding shards do not match frozen plan: missing={missing} extra={extra}")

    order = np.asarray([plan_pos[sample_id] for sample_id in ids], dtype=np.int64).argsort()
    for key in merged:
        merged[key] = merged[key][order]
    if [str(x) for x in merged["sample_id"].tolist()] != plan_ids:
        raise AssertionError("merged embedding order does not match plan order")
    if merged["X"].shape != (len(plan_rows), 384):
        raise ValueError(f"unexpected merged embedding shape: {merged['X'].shape}")
    if not np.isfinite(merged["X"]).all():
        raise ValueError("merged embeddings contain non-finite values")

    counts = Counter(
        f"{role}:{int(label)}"
        for role, label in zip(merged["role"].tolist(), merged["y"].tolist())
    )
    expected = {
        "fit:0": 16_000,
        "fit:1": 16_000,
        "calibration:0": 4_000,
        "calibration:1": 4_000,
        "iid_test:0": 4_000,
        "iid_test:1": 4_000,
        "ood_test:0": 2_000,
        "ood_test:1": 2_000,
    }
    if dict(counts) != expected:
        raise ValueError(f"merged role/class counts differ from 52k protocol: {dict(counts)}")

    metadata = {
        "protocol": MERGE_PROTOCOL,
        "rows": len(plan_rows),
        "embedding_dim": 384,
        "shards": len(shard_npz_paths),
        "plan": str(plan_csv),
        "role_class_counts": dict(counts),
        "validated": False,
        "scientific_status": "pilot_internal_aigenbench",
    }
    out = Path(out_npz)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out,
        X=merged["X"].astype(np.float32),
        y=merged["y"].astype(np.int8),
        role=merged["role"].astype("U16"),
        generator=merged["generator"].astype("U64"),
        origin_dataset=merged["origin_dataset"].astype("U64"),
        sample_id=merged["sample_id"].astype("U160"),
        sample_rank=merged["sample_rank"].astype(np.int32),
        metadata=np.asarray(json.dumps(metadata), dtype="U4096"),
    )
    Path(str(out) + ".metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return metadata
