from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import time
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from PIL import Image

from .second_classifier import (
    AI_GENBENCH_GENERATORS,
    DEFAULT_BACKBONE,
    DEFAULT_OOD_GENERATORS,
    DEFAULT_SEED,
    _stable_seed,
)

HF_DATASET = "lrzpellegrini/AI-GenBench-fake_part"
HF_CONFIG = "default"
HF_DATA_SERVER = "https://datasets-server.huggingface.co"
AIGENBENCH_RAW_BASE = (
    "https://raw.githubusercontent.com/MI-BioLab/AI-GenBench/main/"
    "dataset_creation/resources"
)

REMOTE_MANIFEST_FIELDS = [
    "sample_id",
    "source_split",
    "row_index",
    "label",
    "role",
    "generator",
    "generator_release_date",
    "generator_status",
    "origin_dataset",
    "file_id",
    "sample_rank",
    "source_url",
    "source_kind",
    "local_path",
    "sha256",
    "acquisition_status",
]


def _json_get(url: str, *, timeout: int = 90, retries: int = 4) -> dict:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MFLab-second-classifier/0.1"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - network behavior
            last = exc
            if attempt + 1 < retries:
                time.sleep(min(8.0, 0.75 * (2**attempt)))
    raise RuntimeError(f"request failed after {retries} attempts: {url}") from last


def _download_bytes(url: str, *, timeout: int = 120, retries: int = 4) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MFLab-second-classifier/0.1"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - network behavior
            last = exc
            if attempt + 1 < retries:
                time.sleep(min(8.0, 0.75 * (2**attempt)))
    raise RuntimeError(f"download failed after {retries} attempts: {url}") from last


def _safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)
    return cleaned.strip("._")[:96] or "sample"


def _image_src(value) -> str | None:
    """Extract a Dataset Viewer image URL without depending on one JSON shape."""
    if isinstance(value, str):
        if value.startswith("http://") or value.startswith("https://"):
            return value
        return None
    if isinstance(value, dict):
        for key in ("src", "url", "href"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate:
                return urllib.parse.urljoin(HF_DATA_SERVER + "/", candidate)
        for child in value.values():
            found = _image_src(child)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = _image_src(child)
            if found:
                return found
    return None


def _filter_url(split: str, generator: str, offset: int, length: int = 100) -> str:
    query = urllib.parse.urlencode(
        {
            "dataset": HF_DATASET,
            "config": HF_CONFIG,
            "split": split,
            "where": f'"generator"=\'{generator}\'',
            "offset": int(offset),
            "length": int(length),
        }
    )
    return f"{HF_DATA_SERVER}/filter?{query}"


def fetch_generator_rows(
    split: str,
    generator: str,
    *,
    cache_dir: str | Path | None = None,
    page_size: int = 100,
) -> list[dict]:
    """Fetch metadata + image URLs for one generator from HF Dataset Viewer.

    The endpoint is paginated and the response is cached page-by-page, making
    interrupted runs resumable. No Parquet shard is downloaded by this helper.
    """
    if split not in {"train", "validation"}:
        raise ValueError(f"unsupported split: {split}")
    if generator not in AI_GENBENCH_GENERATORS:
        raise ValueError(f"unknown AI-GenBench generator: {generator}")
    cache_root = Path(cache_dir) if cache_dir else None
    rows: list[dict] = []
    offset = 0
    while True:
        cache_file = None
        if cache_root is not None:
            cache_file = (
                cache_root
                / "hf-pages"
                / split
                / _safe_name(generator)
                / f"{offset:06d}.json"
            )
        if cache_file is not None and cache_file.is_file():
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
        else:
            payload = _json_get(_filter_url(split, generator, offset, page_size))
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
            row_idx = item.get("row_idx")
            if row_idx is None:
                row_idx = item.get("row_index")
            if row_idx is None:
                raise ValueError("Dataset Viewer row has no row index")
            rows.append(
                {
                    "row_index": int(row_idx),
                    "source_split": split,
                    "label": int(row.get("label", 1)),
                    "generator": str(row.get("generator") or generator),
                    "origin_dataset": str(row.get("origin_dataset") or ""),
                    "file_id": str(row.get("file_id") or f"{split}:{row_idx}"),
                    "source_url": _image_src(row.get("image")) or "",
                }
            )
        if len(page) < page_size:
            break
        offset += len(page)
    return rows


def _deterministic_take(
    rows: Sequence[dict], count: int, seed: int, *salt: str
) -> list[dict]:
    if count < 0:
        raise ValueError("count must be >= 0")
    if len(rows) < count:
        raise ValueError(f"requested {count} rows from only {len(rows)} candidates")
    rng = np.random.default_rng(_stable_seed(seed, *salt))
    order = rng.permutation(len(rows))
    return [dict(rows[int(i)]) for i in order[:count]]


def _fake_manifest_row(row: dict, role: str, status: str, rank: int | None = None) -> dict:
    generator = str(row["generator"])
    return {
        "sample_id": f"hf-fake:{row['source_split']}:{int(row['row_index'])}",
        "source_split": str(row["source_split"]),
        "row_index": int(row["row_index"]),
        "label": 1,
        "role": role,
        "generator": generator,
        "generator_release_date": AI_GENBENCH_GENERATORS.get(generator, ""),
        "generator_status": status,
        "origin_dataset": str(row.get("origin_dataset") or ""),
        "file_id": str(row.get("file_id") or ""),
        "sample_rank": "" if rank is None else int(rank),
        "source_url": str(row.get("source_url") or ""),
        "source_kind": "hf_dataset_viewer",
        "local_path": "",
        "sha256": "",
        "acquisition_status": "planned",
    }


def _official_real_filelist_url(split: str) -> str:
    if split not in {"train", "validation"}:
        raise ValueError(split)
    return f"{AIGENBENCH_RAW_BASE}/{split}_real_file_ids.txt"


def load_official_real_file_ids(
    split: str, *, cache_dir: str | Path | None = None
) -> list[str]:
    cache_file = None
    if cache_dir is not None:
        cache_file = Path(cache_dir) / "official-real-filelists" / f"{split}.txt"
    if cache_file is not None and cache_file.is_file():
        text = cache_file.read_text(encoding="utf-8")
    else:
        text = _download_bytes(_official_real_filelist_url(split)).decode("utf-8")
        if cache_file is not None:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(text, encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def _origin_prefix(file_id: str) -> str:
    return file_id.split("/", 1)[0]


def _balanced_file_ids(
    file_ids: Sequence[str],
    total: int,
    seed: int,
    salt: str,
    *,
    allowed_prefixes: Sequence[str] = ("COCO2017_train", "COCO2017_val", "LAION-400M"),
) -> list[str]:
    groups: dict[str, list[str]] = defaultdict(list)
    allowed = set(allowed_prefixes)
    for file_id in file_ids:
        prefix = _origin_prefix(file_id)
        if prefix in allowed:
            groups[prefix].append(file_id)
    queues: dict[str, list[str]] = {}
    for prefix, values in sorted(groups.items()):
        rng = np.random.default_rng(_stable_seed(seed, salt, prefix))
        order = rng.permutation(len(values))
        queues[prefix] = [values[int(i)] for i in order]
    positions = {key: 0 for key in queues}
    chosen: list[str] = []
    while len(chosen) < total:
        progressed = False
        for prefix in sorted(queues):
            pos = positions[prefix]
            if pos < len(queues[prefix]):
                chosen.append(queues[prefix][pos])
                positions[prefix] = pos + 1
                progressed = True
                if len(chosen) == total:
                    break
        if not progressed:
            break
    if len(chosen) < total:
        raise ValueError(
            f"only {len(chosen)} supported real samples available; requested {total}"
        )
    return chosen


def _laion_filelist_zip_url(split: str) -> str:
    if split not in {"train", "validation"}:
        raise ValueError(split)
    return f"{AIGENBENCH_RAW_BASE}/{split}_laion400m_filelist.zip"


def load_laion_url_index(
    split: str, *, cache_dir: str | Path | None = None
) -> dict[str, str]:
    """Load only the official LAION URL manifest, not the images themselves."""
    cache_file = None
    if cache_dir is not None:
        cache_file = Path(cache_dir) / "laion-url-index" / f"{split}.json"
        if cache_file.is_file():
            return json.loads(cache_file.read_text(encoding="utf-8"))

    raw_zip = _download_bytes(_laion_filelist_zip_url(split))
    with zipfile.ZipFile(io.BytesIO(raw_zip), "r") as zf:
        json_names = [name for name in zf.namelist() if name.lower().endswith(".json")]
        if not json_names:
            raise ValueError("official LAION filelist ZIP contains no JSON")
        payload = json.loads(zf.read(json_names[0]).decode("utf-8"))

    index: dict[str, str] = {}
    entries: Iterable = payload.values() if isinstance(payload, dict) else payload
    for item in entries:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("id") or item.get("file_id") or item.get("key")
        url = item.get("url") or item.get("URL") or item.get("image_url")
        if raw_id is None or not url:
            continue
        file_id = str(raw_id)
        if not file_id.startswith("LAION-400M/"):
            file_id = f"LAION-400M/{file_id}"
        index[file_id] = str(url)
    if not index:
        raise ValueError("could not parse any LAION URLs from official filelist")
    if cache_file is not None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(index), encoding="utf-8")
    return index


def resolve_real_url(file_id: str, *, laion_index: dict[str, str] | None = None) -> tuple[str, str]:
    prefix, _, suffix = file_id.partition("/")
    filename = Path(suffix).name
    if prefix == "COCO2017_train":
        return f"https://images.cocodataset.org/train2017/{filename}", "coco"
    if prefix == "COCO2017_val":
        return f"https://images.cocodataset.org/val2017/{filename}", "coco"
    if prefix == "LAION-400M":
        if laion_index is None:
            return "", "laion_index_required"
        return str(laion_index.get(file_id) or ""), "laion"
    return "", "unsupported_real_origin"


def _real_manifest_row(
    split: str,
    file_id: str,
    role: str,
    *,
    source_url: str,
    source_kind: str,
    rank: int | None = None,
) -> dict:
    return {
        "sample_id": f"real:{split}:{file_id}",
        "source_split": split,
        "row_index": -1,
        "label": 0,
        "role": role,
        "generator": "(Real)",
        "generator_release_date": "",
        "generator_status": "real",
        "origin_dataset": _origin_prefix(file_id),
        "file_id": file_id,
        "sample_rank": "" if rank is None else int(rank),
        "source_url": source_url,
        "source_kind": source_kind,
        "local_path": "",
        "sha256": "",
        "acquisition_status": "planned" if source_url else "unresolved",
    }


def _validate_remote_manifest(rows: Sequence[dict], ood_generators: Sequence[str]) -> dict:
    ids = [str(row["sample_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate sample IDs in remote manifest")
    role_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"real": 0, "synthetic": 0})
    fit_generators: set[str] = set()
    ood_observed: set[str] = set()
    for row in rows:
        label = int(row["label"])
        role = str(row["role"])
        role_counts[role]["synthetic" if label else "real"] += 1
        if label and role == "fit":
            fit_generators.add(str(row["generator"]))
        if label and role == "ood_test":
            ood_observed.add(str(row["generator"]))
    for role, counts in role_counts.items():
        if counts["real"] != counts["synthetic"]:
            raise ValueError(f"class imbalance in {role}: {counts}")
    if fit_generators & ood_observed:
        raise ValueError("generator leakage between fit and OOD")
    if ood_observed != set(ood_generators):
        raise ValueError(
            f"OOD generators mismatch: expected={sorted(ood_generators)} observed={sorted(ood_observed)}"
        )
    return {
        "rows": len(rows),
        "roles": dict(role_counts),
        "fit_generators": sorted(fit_generators, key=lambda g: AI_GENBENCH_GENERATORS[g]),
        "ood_generators": sorted(ood_observed, key=lambda g: AI_GENBENCH_GENERATORS[g]),
    }


def build_selective_plan(
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
    """Build a 52k-style plan without downloading full AI-GenBench image shards."""
    ood = tuple(ood_generators)
    seen = tuple(g for g in AI_GENBENCH_GENERATORS if g not in set(ood))
    rows: list[dict] = []

    # Synthetic: fetch only Dataset Viewer metadata/image links. We scan each
    # generator once and then sample deterministically within that generator.
    for generator in seen:
        candidates = fetch_generator_rows("train", generator, cache_dir=cache_dir)
        selected = _deterministic_take(
            candidates, fit_per_generator, seed, "remote-fit", generator
        )
        for rank, row in enumerate(selected, 1):
            rows.append(_fake_manifest_row(row, "fit", "seen", rank))

    for generator in seen:
        candidates = fetch_generator_rows("validation", generator, cache_dir=cache_dir)
        selected = _deterministic_take(
            candidates,
            calibration_per_generator + iid_test_per_generator,
            seed,
            "remote-seen-validation",
            generator,
        )
        for row in selected[:calibration_per_generator]:
            rows.append(_fake_manifest_row(row, "calibration", "seen"))
        for row in selected[calibration_per_generator:]:
            rows.append(_fake_manifest_row(row, "iid_test", "seen"))

    for generator in ood:
        candidates = fetch_generator_rows("validation", generator, cache_dir=cache_dir)
        selected = _deterministic_take(
            candidates, ood_per_generator, seed, "remote-ood", generator
        )
        for row in selected:
            rows.append(_fake_manifest_row(row, "ood_test", "ood"))

    # Real controls: use the exact official AI-GenBench file-ID lists, but only
    # select supported COCO/LAION rows. This avoids requiring the full real set.
    train_ids = load_official_real_file_ids("train", cache_dir=cache_dir)
    val_ids = load_official_real_file_ids("validation", cache_dir=cache_dir)
    laion_train = load_laion_url_index("train", cache_dir=cache_dir)
    laion_val = load_laion_url_index("validation", cache_dir=cache_dir)

    fit_n = len(seen) * fit_per_generator
    fit_real = _balanced_file_ids(train_ids, fit_n, seed, "remote-fit-real")
    for rank, file_id in enumerate(fit_real, 1):
        url, kind = resolve_real_url(file_id, laion_index=laion_train)
        rows.append(
            _real_manifest_row(
                "train", file_id, "fit", source_url=url, source_kind=kind, rank=rank
            )
        )

    n_cal = len(seen) * calibration_per_generator
    n_iid = len(seen) * iid_test_per_generator
    n_ood = len(ood) * ood_per_generator
    val_real = _balanced_file_ids(
        val_ids, n_cal + n_iid + n_ood, seed, "remote-validation-real"
    )
    cursor = 0
    for role, count in (("calibration", n_cal), ("iid_test", n_iid), ("ood_test", n_ood)):
        for file_id in val_real[cursor : cursor + count]:
            url, kind = resolve_real_url(file_id, laion_index=laion_val)
            rows.append(
                _real_manifest_row(
                    "validation", file_id, role, source_url=url, source_kind=kind
                )
            )
        cursor += count

    summary = _validate_remote_manifest(rows, ood)
    unresolved = sum(1 for row in rows if not row.get("source_url"))
    summary.update(
        {
            "protocol": "MFLAB-SCI-AIGENBENCH-SECOND-SELECTIVE-0.1",
            "seed": int(seed),
            "hf_dataset": HF_DATASET,
            "unresolved_source_urls": int(unresolved),
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
        writer = csv.DictWriter(handle, fieldnames=REMOTE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    out.with_suffix(out.suffix + ".summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


def _detect_extension(raw: bytes) -> str:
    with Image.open(io.BytesIO(raw)) as img:
        img.verify()
        fmt = (img.format or "").upper()
    return {
        "JPEG": ".jpg",
        "PNG": ".png",
        "WEBP": ".webp",
        "TIFF": ".tif",
        "BMP": ".bmp",
    }.get(fmt, ".img")


def materialize_plan(
    plan_csv: str | Path,
    output_dir: str | Path,
    out_csv: str | Path,
    *,
    max_samples: int | None = None,
) -> dict:
    """Download only planned images, preserve bytes, verify decode and SHA-256."""
    with Path(plan_csv).open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if max_samples is not None:
        rows = rows[: int(max_samples)]

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    completed = failed = skipped = 0
    total_bytes = 0

    for row in rows:
        source_url = str(row.get("source_url") or "")
        if not source_url:
            row["acquisition_status"] = "unresolved"
            failed += 1
            continue
        digest_name = hashlib.sha256(str(row["sample_id"]).encode("utf-8")).hexdigest()[:20]
        role = _safe_name(str(row["role"]))
        klass = "synthetic" if int(row["label"]) else "real"
        generator = _safe_name(str(row["generator"]))
        target_dir = root / role / klass / generator
        existing = list(target_dir.glob(f"{digest_name}.*")) if target_dir.is_dir() else []
        if existing:
            raw = existing[0].read_bytes()
            try:
                _detect_extension(raw)
                row["local_path"] = str(existing[0])
                row["sha256"] = hashlib.sha256(raw).hexdigest()
                row["acquisition_status"] = "cached"
                skipped += 1
                total_bytes += len(raw)
                continue
            except Exception:
                existing[0].unlink(missing_ok=True)
        try:
            raw = _download_bytes(source_url)
            ext = _detect_extension(raw)
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"{digest_name}{ext}"
            target.write_bytes(raw)
            row["local_path"] = str(target)
            row["sha256"] = hashlib.sha256(raw).hexdigest()
            row["acquisition_status"] = "downloaded"
            completed += 1
            total_bytes += len(raw)
        except Exception as exc:  # pragma: no cover - network/content behavior
            row["acquisition_status"] = "failed"
            row["local_path"] = ""
            row["sha256"] = ""
            row["source_kind"] = f"{row.get('source_kind','')}; error={type(exc).__name__}"
            failed += 1

    out = Path(out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REMOTE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "protocol": "MFLAB-SCI-AIGENBENCH-SECOND-SELECTIVE-0.1",
        "rows_attempted": len(rows),
        "downloaded": completed,
        "cached": skipped,
        "failed_or_unresolved": failed,
        "bytes_materialized": int(total_bytes),
        "gib_materialized": float(total_bytes / (1024**3)),
        "output_dir": str(root),
    }
    out.with_suffix(out.suffix + ".summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


def extract_materialized_embeddings(
    manifest_csv: str | Path,
    out_npz: str | Path,
    *,
    backbone: str = DEFAULT_BACKBONE,
    batch_size: int = 32,
    device: str = "auto",
) -> dict:
    """Extract frozen embeddings from the byte-preserving selective sample."""
    try:
        import torch
        from transformers import AutoImageProcessor, AutoModel
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("install MFLab with the second-classifier extras") from exc

    with Path(manifest_csv).open("r", newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("local_path")]
    if not rows:
        raise ValueError("materialized manifest contains no local images")
    if any(not Path(row["local_path"]).is_file() for row in rows):
        raise FileNotFoundError("one or more materialized image paths do not exist")

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoImageProcessor.from_pretrained(backbone)
    model = AutoModel.from_pretrained(backbone).to(device)
    model.eval()
    model.requires_grad_(False)

    features: list[np.ndarray] = []
    for start in range(0, len(rows), batch_size):
        batch_rows = rows[start : start + batch_size]
        images = []
        for row in batch_rows:
            with Image.open(row["local_path"]) as image:
                images.append(image.convert("RGB").copy())
        inputs = processor(images=images, return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.inference_mode():
            output = model(**inputs)
            embedding = output.last_hidden_state[:, 0, :]
        features.extend(embedding.detach().cpu().float().numpy())

    X = np.asarray(features, dtype=np.float32)
    metadata = {
        "protocol": "MFLAB-SCI-AIGENBENCH-SECOND-SELECTIVE-0.1",
        "backbone": backbone,
        "embedding_dim": int(X.shape[1]),
        "rows": int(len(rows)),
        "device_used": device,
        "input_manifest": str(Path(manifest_csv)),
        "byte_preserving_acquisition": True,
    }
    out = Path(out_npz)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out,
        X=X,
        y=np.asarray([int(row["label"]) for row in rows], dtype=np.int8),
        role=np.asarray([str(row["role"]) for row in rows], dtype="U16"),
        generator=np.asarray([str(row["generator"]) for row in rows], dtype="U64"),
        origin_dataset=np.asarray([str(row["origin_dataset"]) for row in rows], dtype="U64"),
        sample_id=np.asarray([str(row["sample_id"]) for row in rows], dtype="U160"),
        sample_rank=np.asarray(
            [int(row["sample_rank"]) if row.get("sample_rank") else 0 for row in rows],
            dtype=np.int32,
        ),
        metadata=np.asarray(json.dumps(metadata), dtype="U4096"),
    )
    return metadata
