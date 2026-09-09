from __future__ import annotations

import csv
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
from PIL import Image

from . import selective_acquisition as sa
from .second_classifier import DEFAULT_SEED, _stable_seed
from .selective_embeddings import validate_materialized_manifest

COCO_ARCHIVES = {
    "COCO2017_train": {
        "url": "https://images.cocodataset.org/zips/train2017.zip",
        "filename": "train2017.zip",
        "member_prefix": "train2017",
    },
    "COCO2017_val": {
        "url": "https://images.cocodataset.org/zips/val2017.zip",
        "filename": "val2017.zip",
        "member_prefix": "val2017",
    },
}

FROZEN_MANIFEST_FIELDS = [
    "sample_id",
    "source_split",
    "label",
    "role",
    "generator",
    "origin_dataset",
    "file_id",
    "sha256",
    "bytes",
    "local_path",
]


def _diag_base(url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    return {
        "url": url,
        "host": parsed.netloc,
        "attempts": 0,
        "http_status": None,
        "final_url": "",
        "exception_type": "",
        "failure_reason": "",
        "elapsed_seconds": 0.0,
    }


def download_bytes_diagnostic(
    url: str,
    *,
    timeout: int = 90,
    retries: int = 4,
) -> tuple[bytes | None, dict]:
    diag = _diag_base(url)
    started = time.monotonic()
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        diag["attempts"] = attempt
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MFLab-second-classifier/0.2"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                diag["http_status"] = response.getcode()
                diag["final_url"] = response.geturl()
                diag["elapsed_seconds"] = round(time.monotonic() - started, 6)
                return raw, diag
        except urllib.error.HTTPError as exc:
            last_exc = exc
            diag["http_status"] = int(exc.code)
            diag["final_url"] = str(exc.geturl() or "")
            diag["exception_type"] = type(exc).__name__
            diag["failure_reason"] = str(exc.reason or exc)
        except Exception as exc:  # pragma: no cover - depends on remote network
            last_exc = exc
            diag["exception_type"] = type(exc).__name__
            diag["failure_reason"] = str(exc)
        if attempt < retries:
            time.sleep(min(8.0, 0.75 * (2 ** (attempt - 1))))
    diag["elapsed_seconds"] = round(time.monotonic() - started, 6)
    if last_exc and not diag["failure_reason"]:
        diag["failure_reason"] = str(last_exc)
    return None, diag


def download_file_resumable(
    url: str,
    target: str | Path,
    *,
    timeout: int = 120,
    retries: int = 5,
    chunk_size: int = 1024 * 1024,
) -> dict:
    """Download a large archive once, resuming a partial file when supported."""
    out = Path(target)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.is_file() and out.stat().st_size > 0:
        return {
            **_diag_base(url),
            "cached": True,
            "bytes": int(out.stat().st_size),
            "final_url": url,
        }

    part = out.with_suffix(out.suffix + ".part")
    started = time.monotonic()
    last: Exception | None = None
    diag = _diag_base(url)
    for attempt in range(1, retries + 1):
        diag["attempts"] = attempt
        start = part.stat().st_size if part.is_file() else 0
        headers = {"User-Agent": "MFLab-second-classifier/0.2"}
        if start:
            headers["Range"] = f"bytes={start}-"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status = response.getcode()
                diag["http_status"] = status
                diag["final_url"] = response.geturl()
                if start and status != 206:
                    start = 0
                    part.unlink(missing_ok=True)
                mode = "ab" if start and status == 206 else "wb"
                with part.open(mode) as handle:
                    while True:
                        block = response.read(chunk_size)
                        if not block:
                            break
                        handle.write(block)
                os.replace(part, out)
                diag["elapsed_seconds"] = round(time.monotonic() - started, 6)
                diag["cached"] = False
                diag["bytes"] = int(out.stat().st_size)
                return diag
        except urllib.error.HTTPError as exc:
            last = exc
            diag["http_status"] = int(exc.code)
            diag["final_url"] = str(exc.geturl() or "")
            diag["exception_type"] = type(exc).__name__
            diag["failure_reason"] = str(exc.reason or exc)
        except Exception as exc:  # pragma: no cover - remote network
            last = exc
            diag["exception_type"] = type(exc).__name__
            diag["failure_reason"] = str(exc)
        if attempt < retries:
            time.sleep(min(15.0, 1.5 * (2 ** (attempt - 1))))
    diag["elapsed_seconds"] = round(time.monotonic() - started, 6)
    raise RuntimeError(
        f"archive download failed after {retries} attempts: {url}; "
        f"{diag['exception_type']}: {diag['failure_reason']}"
    ) from last


def _write_row_bytes(row: dict, raw: bytes, output_root: Path, status: str) -> dict:
    ext = sa._detect_extension(raw)
    digest_name = hashlib.sha256(str(row["sample_id"]).encode("utf-8")).hexdigest()[:20]
    role = sa._safe_name(str(row["role"]))
    klass = "synthetic" if int(row["label"]) else "real"
    generator = sa._safe_name(str(row["generator"]))
    target_dir = output_root / role / klass / generator
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{digest_name}{ext}"
    target.write_bytes(raw)
    row["local_path"] = str(target)
    row["sha256"] = hashlib.sha256(raw).hexdigest()
    row["acquisition_status"] = status
    return row


def _load_rows(path: str | Path, max_samples: int | None = None) -> list[dict]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if max_samples is not None:
        rows = rows[: int(max_samples)]
    return rows


def _write_rows(path: str | Path, rows: Sequence[dict]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sa.REMOTE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _coco_member_name(file_id: str, prefix: str) -> str:
    spec = COCO_ARCHIVES[prefix]
    filename = Path(file_id.split("/", 1)[1]).name
    return f"{spec['member_prefix']}/{filename}"


def materialize_coco_archive_rows(
    rows: Sequence[dict],
    output_root: str | Path,
    archive_cache: str | Path,
    *,
    archive_paths: Mapping[str, str | Path] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Materialize selected COCO rows from official ZIP archives without re-encoding."""
    root = Path(output_root)
    cache = Path(archive_cache)
    archive_paths = dict(archive_paths or {})
    diagnostics: list[dict] = []
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        prefix = str(row["file_id"]).split("/", 1)[0]
        if prefix not in COCO_ARCHIVES:
            raise ValueError(f"unsupported COCO prefix: {prefix}")
        grouped[prefix].append(row)

    for prefix, group in grouped.items():
        spec = COCO_ARCHIVES[prefix]
        archive = Path(archive_paths[prefix]) if prefix in archive_paths else cache / spec["filename"]
        if prefix not in archive_paths:
            archive_diag = download_file_resumable(spec["url"], archive)
            diagnostics.append({"kind": "coco_archive", "prefix": prefix, **archive_diag})
        if not archive.is_file():
            raise FileNotFoundError(archive)
        with zipfile.ZipFile(archive, "r") as zf:
            names = set(zf.namelist())
            for row in group:
                member = _coco_member_name(str(row["file_id"]), prefix)
                if member not in names:
                    row["acquisition_status"] = "failed"
                    diagnostics.append(
                        {
                            "kind": "coco_member",
                            "sample_id": row["sample_id"],
                            "file_id": row["file_id"],
                            "archive": str(archive),
                            "failure_reason": f"member not found: {member}",
                        }
                    )
                    continue
                raw = zf.read(member)
                try:
                    sa._detect_extension(raw)
                except Exception as exc:
                    row["acquisition_status"] = "failed"
                    diagnostics.append(
                        {
                            "kind": "coco_member",
                            "sample_id": row["sample_id"],
                            "file_id": row["file_id"],
                            "archive": str(archive),
                            "exception_type": type(exc).__name__,
                            "failure_reason": str(exc),
                        }
                    )
                    continue
                _write_row_bytes(row, raw, root, "downloaded_coco_archive")
    return list(rows), diagnostics


def _laion_reserve(
    split: str,
    planned_file_ids: set[str],
    *,
    cache_dir: str | Path,
    seed: int,
) -> list[tuple[str, str]]:
    file_ids = sa.load_official_real_file_ids(split, cache_dir=cache_dir)
    index = sa.load_laion_url_index(split, cache_dir=cache_dir)
    candidates = [
        file_id
        for file_id in file_ids
        if file_id.startswith("LAION-400M/")
        and file_id not in planned_file_ids
        and index.get(file_id)
    ]
    rng = np.random.default_rng(_stable_seed(seed, "laion-reserve", split))
    order = rng.permutation(len(candidates))
    return [(candidates[int(i)], index[candidates[int(i)]]) for i in order]


def materialize_stable_plan(
    plan_csv: str | Path,
    output_dir: str | Path,
    out_csv: str | Path,
    *,
    cache_dir: str | Path,
    archive_cache: str | Path | None = None,
    diagnostics_out: str | Path | None = None,
    replacement_log_out: str | Path | None = None,
    max_samples: int | None = None,
    seed: int = DEFAULT_SEED,
    max_laion_replacements_per_sample: int = 8,
    archive_paths: Mapping[str, str | Path] | None = None,
) -> dict:
    """Stable acquisition: synthetic direct, COCO via archive, LAION with audited reserve."""
    rows = _load_rows(plan_csv, max_samples=max_samples)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    diagnostics: list[dict] = []
    replacements: list[dict] = []

    coco_rows = [row for row in rows if str(row.get("source_kind")) == "coco"]
    direct_rows = [row for row in rows if str(row.get("source_kind")) != "coco"]

    planned_laion: dict[str, set[str]] = defaultdict(set)
    for row in direct_rows:
        if str(row.get("source_kind")) == "laion":
            planned_laion[str(row["source_split"])].add(str(row["file_id"]))
    reserve_by_split = {
        split: _laion_reserve(split, ids, cache_dir=cache_dir, seed=seed)
        for split, ids in planned_laion.items()
    }
    reserve_pos = {split: 0 for split in reserve_by_split}

    for row in direct_rows:
        source_url = str(row.get("source_url") or "")
        raw, diag = download_bytes_diagnostic(source_url) if source_url else (None, {
            **_diag_base(source_url),
            "failure_reason": "unresolved source URL",
        })
        diagnostics.append({
            "kind": "direct",
            "sample_id": row.get("sample_id"),
            "file_id": row.get("file_id"),
            "source_kind": row.get("source_kind"),
            **diag,
        })
        if raw is not None:
            try:
                _write_row_bytes(row, raw, root, "downloaded")
                continue
            except Exception as exc:
                diagnostics.append({
                    "kind": "decode",
                    "sample_id": row.get("sample_id"),
                    "file_id": row.get("file_id"),
                    "exception_type": type(exc).__name__,
                    "failure_reason": str(exc),
                })
                raw = None

        if str(row.get("source_kind")) != "laion":
            row["acquisition_status"] = "failed"
            row["local_path"] = ""
            row["sha256"] = ""
            continue

        split = str(row["source_split"])
        reserve = reserve_by_split.get(split, [])
        original = {
            "sample_id": row["sample_id"],
            "file_id": row["file_id"],
            "source_url": row["source_url"],
        }
        success = False
        attempts = 0
        while attempts < max_laion_replacements_per_sample and reserve_pos.get(split, 0) < len(reserve):
            idx = reserve_pos[split]
            reserve_pos[split] = idx + 1
            replacement_file_id, replacement_url = reserve[idx]
            attempts += 1
            replacement_raw, replacement_diag = download_bytes_diagnostic(replacement_url)
            diagnostics.append({
                "kind": "laion_replacement_attempt",
                "replacement_for": original["sample_id"],
                "file_id": replacement_file_id,
                **replacement_diag,
            })
            if replacement_raw is None:
                continue
            candidate = dict(row)
            candidate["sample_id"] = f"real:{split}:{replacement_file_id}"
            candidate["file_id"] = replacement_file_id
            candidate["source_url"] = replacement_url
            candidate["source_kind"] = "laion_replacement"
            try:
                _write_row_bytes(candidate, replacement_raw, root, "downloaded_replacement")
            except Exception as exc:
                diagnostics.append({
                    "kind": "laion_replacement_decode",
                    "replacement_for": original["sample_id"],
                    "file_id": replacement_file_id,
                    "exception_type": type(exc).__name__,
                    "failure_reason": str(exc),
                })
                continue
            row.clear()
            row.update(candidate)
            replacements.append({
                "replacement_for": original,
                "replacement": {
                    "sample_id": row["sample_id"],
                    "file_id": row["file_id"],
                    "source_url": row["source_url"],
                    "sha256": row["sha256"],
                },
                "split": split,
                "replacement_attempts": attempts,
            })
            success = True
            break
        if not success:
            row["acquisition_status"] = "failed"
            row["local_path"] = ""
            row["sha256"] = ""

    if coco_rows:
        _, coco_diag = materialize_coco_archive_rows(
            coco_rows,
            root,
            archive_cache or (Path(cache_dir) / "coco-archives"),
            archive_paths=archive_paths,
        )
        diagnostics.extend(coco_diag)

    _write_rows(out_csv, rows)
    status_counts = Counter(str(row.get("acquisition_status") or "") for row in rows)
    source_counts = Counter(str(row.get("source_kind") or "") for row in rows)
    failed = sum(1 for row in rows if not row.get("local_path") or not row.get("sha256"))
    summary = {
        "protocol": "MFLAB-SCI-AIGENBENCH-DERIVED-ACQUISITION-0.2",
        "corpus_name": "MFLab AI-GenBench-derived v1",
        "rows_attempted": len(rows),
        "failed_or_unresolved": int(failed),
        "replacements": len(replacements),
        "status_counts": dict(status_counts),
        "source_kind_counts": dict(source_counts),
        "coco_strategy": "official_zip_archive",
        "laion_strategy": "deterministic_reserve_with_audit_log",
        "byte_preserving": True,
    }
    Path(str(out_csv) + ".summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    diagnostics_path = Path(diagnostics_out) if diagnostics_out else Path(str(out_csv) + ".diagnostics.json")
    diagnostics_path.write_text(json.dumps(diagnostics, indent=2, ensure_ascii=False), encoding="utf-8")
    replacement_path = Path(replacement_log_out) if replacement_log_out else Path(str(out_csv) + ".replacements.json")
    replacement_path.write_text(json.dumps(replacements, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def freeze_materialized_corpus(
    manifest_csv: str | Path,
    frozen_manifest_csv: str | Path,
    lock_json: str | Path,
    *,
    replacement_log: str | Path | None = None,
) -> dict:
    """Freeze the successfully materialized corpus into a hash-addressed scientific lock."""
    validation = validate_materialized_manifest(manifest_csv)
    with Path(manifest_csv).open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    frozen_rows: list[dict] = []
    seen: set[str] = set()
    role_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    for row in sorted(rows, key=lambda r: (r["role"], r["label"], r["sample_id"])):
        sample_id = str(row["sample_id"])
        if sample_id in seen:
            raise ValueError(f"duplicate sample_id while freezing corpus: {sample_id}")
        seen.add(sample_id)
        path = Path(row["local_path"])
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest.lower() != str(row["sha256"]).lower():
            raise ValueError(f"SHA-256 mismatch while freezing: {sample_id}")
        frozen_rows.append({
            "sample_id": sample_id,
            "source_split": row["source_split"],
            "label": row["label"],
            "role": row["role"],
            "generator": row["generator"],
            "origin_dataset": row["origin_dataset"],
            "file_id": row["file_id"],
            "sha256": digest,
            "bytes": len(raw),
            "local_path": str(path),
        })
        role_counts[f"{row['role']}:{'synthetic' if int(row['label']) else 'real'}"] += 1
        source_counts[str(row["origin_dataset"])] += 1

    frozen = Path(frozen_manifest_csv)
    frozen.parent.mkdir(parents=True, exist_ok=True)
    with frozen.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FROZEN_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(frozen_rows)
    frozen_bytes = frozen.read_bytes()
    manifest_sha = hashlib.sha256(frozen_bytes).hexdigest()

    replacement_sha = ""
    if replacement_log is not None and Path(replacement_log).is_file():
        replacement_sha = hashlib.sha256(Path(replacement_log).read_bytes()).hexdigest()

    lock = {
        "protocol": "MFLAB-SCI-AIGENBENCH-DERIVED-FREEZE-0.1",
        "corpus_name": "MFLab AI-GenBench-derived v1",
        "corpus_id": f"mflab-aigenbench-derived-v1-{manifest_sha[:16]}",
        "rows": len(frozen_rows),
        "frozen_manifest": str(frozen),
        "frozen_manifest_sha256": manifest_sha,
        "replacement_log": str(replacement_log or ""),
        "replacement_log_sha256": replacement_sha,
        "role_class_counts": dict(role_counts),
        "origin_dataset_counts": dict(source_counts),
        "all_sample_sha256_verified": True,
        "byte_preserving_acquisition": True,
        "validation": validation,
    }
    lock_path = Path(lock_json)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")
    return lock
