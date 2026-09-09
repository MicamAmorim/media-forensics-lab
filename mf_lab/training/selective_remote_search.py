from __future__ import annotations

import csv
import json
import urllib.parse
from pathlib import Path
from typing import Sequence

from . import selective_acquisition as sa
from .second_classifier import (
    AI_GENBENCH_GENERATORS,
    DEFAULT_OOD_GENERATORS,
    DEFAULT_SEED,
)


def _search_url(split: str, query: str, offset: int, length: int = 100) -> str:
    params = urllib.parse.urlencode(
        {
            "dataset": sa.HF_DATASET,
            "config": sa.HF_CONFIG,
            "split": split,
            "query": query,
            "offset": int(offset),
            "length": int(length),
        }
    )
    return f"{sa.HF_DATA_SERVER}/search?{params}"


def _expected_generator_rows(split: str) -> int:
    if split == "train":
        return 4000
    if split == "validation":
        return 1000
    raise ValueError(f"unsupported split: {split}")


def fetch_generator_rows_search(
    split: str,
    generator: str,
    *,
    cache_dir: str | Path | None = None,
    page_size: int = 100,
    enforce_expected_count: bool = True,
) -> list[dict]:
    """Enumerate one generator through Dataset Viewer `/search`.

    `/filter` is the semantically ideal endpoint, but the AI-GenBench image
    dataset can time out there because the backend evaluates a large Parquet
    predicate. `/search` uses the viewer's text index instead. MFLab still
    applies an exact local equality check on the `generator` column and, by
    default, requires the official AI-GenBench count (4000 train / 1000
    validation) before any sampling is allowed.
    """
    if split not in {"train", "validation"}:
        raise ValueError(f"unsupported split: {split}")
    if generator not in AI_GENBENCH_GENERATORS:
        raise ValueError(f"unknown AI-GenBench generator: {generator}")

    cache_root = Path(cache_dir) if cache_dir else None
    exact: dict[int, dict] = {}
    offset = 0
    while True:
        cache_file = None
        if cache_root is not None:
            cache_file = (
                cache_root
                / "hf-search-pages"
                / split
                / sa._safe_name(generator)
                / f"{offset:06d}.json"
            )
        if cache_file is not None and cache_file.is_file():
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
        else:
            payload = sa._json_get(
                _search_url(split, generator, offset, page_size),
                timeout=60,
                retries=3,
            )
            if cache_file is not None:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(
                    json.dumps(payload, ensure_ascii=False), encoding="utf-8"
                )

        page = payload.get("rows") or []
        if not page:
            break
        for item in page:
            row = item.get("row") or {}
            if str(row.get("generator") or "") != generator:
                continue
            row_idx = item.get("row_idx")
            if row_idx is None:
                row_idx = item.get("row_index")
            if row_idx is None:
                raise ValueError("Dataset Viewer search row has no row index")
            exact[int(row_idx)] = {
                "row_index": int(row_idx),
                "source_split": split,
                "label": int(row.get("label", 1)),
                "generator": generator,
                "origin_dataset": str(row.get("origin_dataset") or ""),
                "file_id": str(row.get("file_id") or f"{split}:{row_idx}"),
                "source_url": sa._image_src(row.get("image")) or "",
            }
        if len(page) < page_size:
            break
        offset += len(page)

    rows = [exact[idx] for idx in sorted(exact)]
    expected = _expected_generator_rows(split)
    if enforce_expected_count and len(rows) != expected:
        raise RuntimeError(
            f"Dataset Viewer search returned {len(rows)} exact rows for "
            f"{generator!r}/{split}; expected {expected}. Refusing partial sampling."
        )
    if any(not row["source_url"] for row in rows):
        missing = sum(1 for row in rows if not row["source_url"])
        raise RuntimeError(
            f"Dataset Viewer search has {missing} rows without image source URLs for "
            f"{generator!r}/{split}"
        )
    return rows


def build_selective_plan_search(
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
    """Build the selective pilot using the search-index acquisition backend."""
    ood = tuple(ood_generators)
    unknown = [g for g in ood if g not in AI_GENBENCH_GENERATORS]
    if unknown:
        raise ValueError(f"unknown OOD generators: {unknown}")
    seen = tuple(g for g in AI_GENBENCH_GENERATORS if g not in set(ood))
    rows: list[dict] = []

    for generator in seen:
        candidates = fetch_generator_rows_search("train", generator, cache_dir=cache_dir)
        selected = sa._deterministic_take(
            candidates, fit_per_generator, seed, "remote-fit", generator
        )
        for rank, row in enumerate(selected, 1):
            rows.append(sa._fake_manifest_row(row, "fit", "seen", rank))

    for generator in seen:
        candidates = fetch_generator_rows_search(
            "validation", generator, cache_dir=cache_dir
        )
        selected = sa._deterministic_take(
            candidates,
            calibration_per_generator + iid_test_per_generator,
            seed,
            "remote-seen-validation",
            generator,
        )
        for row in selected[:calibration_per_generator]:
            rows.append(sa._fake_manifest_row(row, "calibration", "seen"))
        for row in selected[calibration_per_generator:]:
            rows.append(sa._fake_manifest_row(row, "iid_test", "seen"))

    for generator in ood:
        candidates = fetch_generator_rows_search(
            "validation", generator, cache_dir=cache_dir
        )
        selected = sa._deterministic_take(
            candidates, ood_per_generator, seed, "remote-ood", generator
        )
        for row in selected:
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
            "protocol": "MFLAB-SCI-AIGENBENCH-SECOND-SELECTIVE-SEARCH-0.2",
            "seed": int(seed),
            "hf_dataset": sa.HF_DATASET,
            "remote_backend": "dataset_viewer_search_exact_generator_gate",
            "unresolved_source_urls": 0,
            "full_fake_dataset_download_required": False,
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
