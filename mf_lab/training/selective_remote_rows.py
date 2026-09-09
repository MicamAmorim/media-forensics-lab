from __future__ import annotations

import csv
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from . import selective_acquisition as sa
from .second_classifier import (
    AI_GENBENCH_GENERATORS,
    DEFAULT_OOD_GENERATORS,
    DEFAULT_SEED,
    _stable_seed,
)

SPLIT_ROWS = {"train": 144_000, "validation": 36_000}


def _rows_url(split: str, offset: int, length: int = 100) -> str:
    params = urllib.parse.urlencode(
        {
            "dataset": sa.HF_DATASET,
            "config": sa.HF_CONFIG,
            "split": split,
            "offset": int(offset),
            "length": int(length),
        }
    )
    return f"{sa.HF_DATA_SERVER}/rows?{params}"


def _retry_after_seconds(exc: urllib.error.HTTPError, attempt: int) -> float:
    raw = exc.headers.get("Retry-After") if exc.headers is not None else None
    if raw:
        try:
            return max(1.0, min(120.0, float(raw)))
        except ValueError:
            pass
    return min(60.0, 2.0 ** min(attempt, 6))


def _rows_json_get(
    url: str,
    *,
    timeout: int = 60,
    retries: int = 8,
) -> tuple[dict, dict]:
    """Dataset Viewer GET with explicit 429 handling and auditable retry metadata."""
    last: Exception | None = None
    rate_limit_hits = 0
    started = time.monotonic()
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MFLab-second-classifier/0.3"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return payload, {
                    "attempts": attempt,
                    "rate_limit_hits": rate_limit_hits,
                    "elapsed_seconds": round(time.monotonic() - started, 6),
                    "http_status": response.getcode(),
                }
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code == 429:
                rate_limit_hits += 1
                wait = _retry_after_seconds(exc, attempt)
            else:
                wait = min(20.0, 1.5 * (2 ** (attempt - 1)))
        except Exception as exc:  # pragma: no cover - network behavior
            last = exc
            wait = min(20.0, 1.5 * (2 ** (attempt - 1)))
        if attempt < retries:
            time.sleep(wait)
    raise RuntimeError(
        f"Dataset Viewer request failed after {retries} attempts: {url}"
    ) from last


def _page_order(split: str, page_size: int, seed: int) -> list[int]:
    if split not in SPLIT_ROWS:
        raise ValueError(f"unsupported split: {split}")
    n_pages = math.ceil(SPLIT_ROWS[split] / page_size)
    rng = np.random.default_rng(_stable_seed(seed, "dataset-viewer-rows-pages", split))
    return [int(x) for x in rng.permutation(n_pages)]


def _parse_viewer_row(item: dict, split: str) -> dict:
    row = item.get("row") or {}
    row_idx = item.get("row_idx")
    if row_idx is None:
        row_idx = item.get("row_index")
    if row_idx is None:
        raise ValueError("Dataset Viewer row has no row index")
    return {
        "row_index": int(row_idx),
        "source_split": split,
        "label": int(row.get("label", 1)),
        "generator": str(row.get("generator") or ""),
        "origin_dataset": str(row.get("origin_dataset") or ""),
        "file_id": str(row.get("file_id") or f"{split}:{row_idx}"),
        "source_url": sa._image_src(row.get("image")) or "",
    }


def fetch_generator_quota_rows(
    split: str,
    quotas: Mapping[str, int],
    *,
    cache_dir: str | Path | None = None,
    seed: int = DEFAULT_SEED,
    page_size: int = 100,
    headroom: float = 0.10,
    request_delay_seconds: float = 1.0,
) -> tuple[dict[str, list[dict]], dict]:
    """Collect a reproducible per-generator sample through `/rows` only.

    Pages are visited in a deterministic pseudorandom order over the entire
    split. Network pages are cached and deliberately throttled. HTTP 429 obeys
    Retry-After when available and otherwise uses exponential backoff. A failed
    run can therefore resume from its cached pages instead of restarting from
    page zero.
    """
    if split not in SPLIT_ROWS:
        raise ValueError(f"unsupported split: {split}")
    normalized = {str(g): int(n) for g, n in quotas.items() if int(n) > 0}
    unknown = [g for g in normalized if g not in AI_GENBENCH_GENERATORS]
    if unknown:
        raise ValueError(f"unknown generators: {unknown}")
    if not normalized:
        return {}, {
            "split": split,
            "pages_fetched": 0,
            "rows_scanned": 0,
            "network_requests": 0,
            "cache_hits": 0,
            "rate_limit_hits": 0,
        }

    targets = {
        g: max(n, int(math.ceil(n * (1.0 + max(0.0, headroom)))))
        for g, n in normalized.items()
    }
    buckets: dict[str, dict[int, dict]] = {g: {} for g in normalized}
    cache_root = Path(cache_dir) if cache_dir else None
    pages_fetched = 0
    rows_scanned = 0
    network_requests = 0
    cache_hits = 0
    rate_limit_hits = 0
    request_attempts = 0
    order = _page_order(split, page_size, seed)

    for page_index in order:
        offset = page_index * page_size
        length = min(page_size, SPLIT_ROWS[split] - offset)
        cache_file = None
        if cache_root is not None:
            cache_file = (
                cache_root / "hf-row-pages" / split / f"{offset:06d}-{length:03d}.json"
            )
        if cache_file is not None and cache_file.is_file():
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            cache_hits += 1
        else:
            payload, request_meta = _rows_json_get(_rows_url(split, offset, length))
            network_requests += 1
            rate_limit_hits += int(request_meta.get("rate_limit_hits", 0))
            request_attempts += int(request_meta.get("attempts", 1))
            if cache_file is not None:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(
                    json.dumps(payload, ensure_ascii=False), encoding="utf-8"
                )
            if request_delay_seconds > 0:
                time.sleep(float(request_delay_seconds))

        page = payload.get("rows") or []
        if not page:
            raise RuntimeError(
                f"Dataset Viewer /rows returned an empty page for {split} offset={offset}"
            )
        pages_fetched += 1
        rows_scanned += len(page)
        for item in page:
            parsed = _parse_viewer_row(item, split)
            generator = parsed["generator"]
            if generator in buckets:
                buckets[generator][int(parsed["row_index"])] = parsed

        if all(len(buckets[g]) >= targets[g] for g in normalized):
            break

    missing = {
        g: normalized[g] - len(buckets[g])
        for g in normalized
        if len(buckets[g]) < normalized[g]
    }
    if missing:
        raise RuntimeError(
            f"could not satisfy generator quotas from /rows for split {split}: {missing}"
        )

    selected: dict[str, list[dict]] = {}
    for generator, quota in normalized.items():
        candidates = [buckets[generator][idx] for idx in sorted(buckets[generator])]
        if any(not row["source_url"] for row in candidates):
            candidates = [row for row in candidates if row["source_url"]]
        if len(candidates) < quota:
            raise RuntimeError(
                f"only {len(candidates)} usable image URLs for {generator!r}/{split}; need {quota}"
            )
        selected[generator] = sa._deterministic_take(
            candidates,
            quota,
            seed,
            "rows-final-sample",
            split,
            generator,
        )

    summary = {
        "split": split,
        "backend": "dataset_viewer_rows_random_page_scan",
        "page_size": int(page_size),
        "pages_fetched": int(pages_fetched),
        "rows_scanned": int(rows_scanned),
        "fraction_of_split_scanned": float(rows_scanned / SPLIT_ROWS[split]),
        "requested_quotas": normalized,
        "candidate_counts": {g: len(buckets[g]) for g in normalized},
        "headroom": float(headroom),
        "request_delay_seconds": float(request_delay_seconds),
        "network_requests": int(network_requests),
        "cache_hits": int(cache_hits),
        "request_attempts": int(request_attempts),
        "rate_limit_hits": int(rate_limit_hits),
    }
    return selected, summary


def build_selective_plan_rows(
    out_csv: str | Path,
    *,
    cache_dir: str | Path,
    fit_per_generator: int = 500,
    calibration_per_generator: int = 125,
    iid_test_per_generator: int = 125,
    ood_per_generator: int = 500,
    ood_generators: Sequence[str] = DEFAULT_OOD_GENERATORS,
    seed: int = DEFAULT_SEED,
) -> dict:
    """Build the 52k pilot plan using only random-access `/rows` pages."""
    ood = tuple(ood_generators)
    unknown = [g for g in ood if g not in AI_GENBENCH_GENERATORS]
    if unknown:
        raise ValueError(f"unknown OOD generators: {unknown}")
    seen = tuple(g for g in AI_GENBENCH_GENERATORS if g not in set(ood))

    train_selected, train_scan = fetch_generator_quota_rows(
        "train",
        {g: fit_per_generator for g in seen},
        cache_dir=cache_dir,
        seed=seed,
    )
    validation_quotas = {
        **{g: calibration_per_generator + iid_test_per_generator for g in seen},
        **{g: ood_per_generator for g in ood},
    }
    val_selected, val_scan = fetch_generator_quota_rows(
        "validation",
        validation_quotas,
        cache_dir=cache_dir,
        seed=seed,
    )

    rows: list[dict] = []
    for generator in seen:
        for rank, row in enumerate(train_selected[generator], 1):
            rows.append(sa._fake_manifest_row(row, "fit", "seen", rank))

    for generator in seen:
        selected = val_selected[generator]
        for row in selected[:calibration_per_generator]:
            rows.append(sa._fake_manifest_row(row, "calibration", "seen"))
        for row in selected[calibration_per_generator:]:
            rows.append(sa._fake_manifest_row(row, "iid_test", "seen"))

    for generator in ood:
        for row in val_selected[generator]:
            rows.append(sa._fake_manifest_row(row, "ood_test", "ood"))

    train_ids = sa.load_official_real_file_ids("train", cache_dir=cache_dir)
    val_ids = sa.load_official_real_file_ids("validation", cache_dir=cache_dir)
    laion_train = sa.load_laion_url_index("train", cache_dir=cache_dir)
    laion_val = sa.load_laion_url_index("validation", cache_dir=cache_dir)

    fit_n = len(seen) * fit_per_generator
    fit_real = sa._balanced_file_ids(train_ids, fit_n, seed, "remote-fit-real")
    for rank, file_id in enumerate(fit_real, 1):
        url, kind = sa.resolve_real_url(file_id, laion_index=laion_train)
        rows.append(
            sa._real_manifest_row(
                "train", file_id, "fit", source_url=url, source_kind=kind, rank=rank
            )
        )

    n_cal = len(seen) * calibration_per_generator
    n_iid = len(seen) * iid_test_per_generator
    n_ood = len(ood) * ood_per_generator
    val_real = sa._balanced_file_ids(
        val_ids, n_cal + n_iid + n_ood, seed, "remote-validation-real"
    )
    cursor = 0
    for role, count in (
        ("calibration", n_cal),
        ("iid_test", n_iid),
        ("ood_test", n_ood),
    ):
        for file_id in val_real[cursor : cursor + count]:
            url, kind = sa.resolve_real_url(file_id, laion_index=laion_val)
            rows.append(
                sa._real_manifest_row(
                    "validation", file_id, role, source_url=url, source_kind=kind
                )
            )
        cursor += count

    summary = sa._validate_remote_manifest(rows, ood)
    unresolved = sum(1 for row in rows if not row.get("source_url"))
    if unresolved:
        raise RuntimeError(f"selective plan contains {unresolved} unresolved source URLs")
    summary.update(
        {
            "protocol": "MFLAB-SCI-AIGENBENCH-SECOND-SELECTIVE-ROWS-0.4",
            "seed": int(seed),
            "hf_dataset": sa.HF_DATASET,
            "remote_backend": "dataset_viewer_rows_random_page_scan_rate_limited",
            "unresolved_source_urls": 0,
            "full_fake_dataset_download_required": False,
            "scan": {"train": train_scan, "validation": val_scan},
            "sampling": {
                "fit_per_seen_generator": int(fit_per_generator),
                "calibration_per_seen_generator": int(calibration_per_generator),
                "iid_test_per_seen_generator": int(iid_test_per_generator),
                "ood_per_generator": int(ood_per_generator),
            },
        }
    )

    out = Path(out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sa.REMOTE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    out.with_suffix(out.suffix + ".summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary
