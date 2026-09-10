from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


# Chronology copied from the official AI-GenBench metadata file so that the
# MFLab split is reproducible and auditable. Keep this list synchronized with
# upstream before a new scientific validation run.
AI_GENBENCH_GENERATORS: dict[str, str] = {
    "CycleGAN": "2017-03-30",
    "Cascaded Refinement Networks": "2017-07-28",
    "ProGAN": "2017-10-27",
    "StarGAN": "2017-11-24",
    "SN-PatchGAN": "2018-06-10",
    "BigGAN": "2018-09-28",
    "IMLE": "2018-11-29",
    "StyleGAN1": "2018-12-12",
    "GauGAN": "2019-03-18",
    "StyleGAN2": "2019-12-03",
    "DDPM": "2020-06-19",
    "CIPS": "2020-11-27",
    "VQGAN": "2020-12-17",
    "GANformer": "2021-03-01",
    "ADM": "2021-05-11",
    "StyleGAN3": "2021-06-23",
    "LaMa": "2021-09-15",
    "FaceSynthetics": "2021-09-30",
    "ProjectedGAN": "2021-11-01",
    "Palette": "2021-11-10",
    "VQ-Diffusion": "2021-11-29",
    "Denoising Diffusion GAN": "2021-12-16",
    "Glide": "2021-12-20",
    "Latent Diffusion": "2021-12-21",
    "Midjourney": "2022-02-01",
    "MAT": "2022-03-29",
    "Diffusion GAN (ProjectedGAN)": "2022-06-05",
    "Diffusion GAN (StyleGAN2)": "2022-06-06",
    "Stable Diffusion 1.4": "2022-08-22",
    "Stable Diffusion 1.5": "2022-10-20",
    "Stable Diffusion 2.1": "2022-12-07",
    "DeepFloyd IF": "2023-04-26",
    "Stable Diffusion XL 1.0": "2023-07-26",
    "DALL-E 3": "2023-09-20",
    "FLUX 1 Dev": "2024-08-01",
    "FLUX 1 Schnell": "2024-08-02",
}

# Mirrors the benchmark's four-generator sliding-window idea: train on the past,
# then evaluate on the immediate future without leaking those generators into fit.
DEFAULT_OOD_GENERATORS: tuple[str, ...] = tuple(
    name for name, _ in sorted(AI_GENBENCH_GENERATORS.items(), key=lambda kv: kv[1])[-4:]
)

DEFAULT_BACKBONE = "facebook/dinov2-small"
DEFAULT_MODEL_NAME = "mflab_aigenbench_dinov2s14_logreg_calibrated_v1"
DEFAULT_SEED = 20260909

MANIFEST_FIELDS = [
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
]


def _stable_seed(seed: int, *parts: str) -> int:
    h = hashlib.sha256()
    h.update(str(seed).encode("utf-8"))
    for part in parts:
        h.update(b"\0")
        h.update(str(part).encode("utf-8"))
    return int.from_bytes(h.digest()[:8], "big", signed=False)


def _permute(values: Sequence[int], seed: int, *salt: str) -> list[int]:
    arr = np.asarray(values, dtype=np.int64)
    rng = np.random.default_rng(_stable_seed(seed, *salt))
    if len(arr):
        arr = arr[rng.permutation(len(arr))]
    return [int(x) for x in arr.tolist()]


def _round_robin_balanced_indices(
    rows: Sequence[dict], total: int, seed: int, salt: str
) -> list[int]:
    """Select real-image row indices while limiting origin-dataset dominance.

    Each origin dataset is shuffled independently and then sampled round-robin.
    Small origins are exhausted without replacement and remaining origins fill the
    requested quota. No image is duplicated.
    """
    if total <= 0:
        return []
    groups: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("origin_dataset") or "(unknown)")].append(int(row["row_index"]))
    queues: dict[str, list[int]] = {
        name: _permute(indices, seed, salt, name) for name, indices in sorted(groups.items())
    }
    positions = {name: 0 for name in queues}
    chosen: list[int] = []
    while len(chosen) < total:
        progressed = False
        for name in sorted(queues):
            pos = positions[name]
            queue = queues[name]
            if pos < len(queue):
                chosen.append(queue[pos])
                positions[name] = pos + 1
                progressed = True
                if len(chosen) >= total:
                    break
        if not progressed:
            break
    if len(chosen) < total:
        raise ValueError(f"requested {total} real rows but only {len(chosen)} were available")
    return chosen


def _metadata_rows(split, split_name: str) -> list[dict]:
    wanted = [c for c in ("label", "generator", "origin_dataset", "file_id") if c in split.column_names]
    if "label" not in wanted or "generator" not in wanted:
        raise ValueError("AI-GenBench split must contain at least label and generator columns")
    meta = split.select_columns(wanted)
    rows: list[dict] = []
    for i in range(len(meta)):
        item = meta[i]
        rows.append(
            {
                "row_index": i,
                "source_split": split_name,
                "label": int(item["label"]),
                "generator": str(item.get("generator") or "(Real)"),
                "origin_dataset": str(item.get("origin_dataset") or ""),
                "file_id": str(item.get("file_id") or f"{split_name}:{i}"),
            }
        )
    return rows


def _manifest_row(row: dict, role: str, status: str, rank: int | None = None) -> dict:
    generator = str(row["generator"])
    return {
        "sample_id": f"{row['source_split']}:{int(row['row_index'])}",
        "source_split": str(row["source_split"]),
        "row_index": int(row["row_index"]),
        "label": int(row["label"]),
        "role": role,
        "generator": generator,
        "generator_release_date": AI_GENBENCH_GENERATORS.get(generator, ""),
        "generator_status": status,
        "origin_dataset": str(row.get("origin_dataset") or ""),
        "file_id": str(row.get("file_id") or ""),
        "sample_rank": "" if rank is None else int(rank),
    }


def _select_synthetic(
    rows: Sequence[dict],
    generators: Sequence[str],
    count_per_generator: int,
    seed: int,
    salt: str,
    role: str,
    status: str,
    offset_per_generator: int = 0,
    ranks: bool = False,
) -> list[dict]:
    by_generator: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if int(row["label"]) == 1 and row["generator"] in generators:
            by_generator[str(row["generator"])].append(row)
    out: list[dict] = []
    for generator in generators:
        candidates = by_generator.get(generator, [])
        ordered_idx = _permute(
            [int(r["row_index"]) for r in candidates], seed, salt, generator
        )
        row_by_idx = {int(r["row_index"]): r for r in candidates}
        selected = ordered_idx[offset_per_generator : offset_per_generator + count_per_generator]
        if len(selected) < count_per_generator:
            raise ValueError(
                f"generator {generator!r} has only {len(selected)} rows for {role}; "
                f"requested {count_per_generator} after offset {offset_per_generator}"
            )
        for local_rank, idx in enumerate(selected, 1):
            rank = local_rank if ranks else None
            out.append(_manifest_row(row_by_idx[idx], role, status, rank))
    return out


def _validate_manifest_rows(rows: Sequence[dict], ood_generators: Sequence[str]) -> dict:
    ids = [str(r["sample_id"]) for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("manifest contains duplicate sample_id values")

    fit_generators = {
        str(r["generator"])
        for r in rows
        if r["role"] == "fit" and int(r["label"]) == 1
    }
    ood_test_generators = {
        str(r["generator"])
        for r in rows
        if r["role"] == "ood_test" and int(r["label"]) == 1
    }
    overlap = fit_generators & ood_test_generators
    if overlap:
        raise ValueError(f"generator leakage between fit and OOD test: {sorted(overlap)}")
    expected = set(ood_generators)
    if ood_test_generators != expected:
        raise ValueError(
            f"OOD generator mismatch: expected={sorted(expected)} observed={sorted(ood_test_generators)}"
        )

    by_role: dict[str, dict[str, int]] = defaultdict(lambda: {"real": 0, "synthetic": 0})
    for row in rows:
        key = "synthetic" if int(row["label"]) == 1 else "real"
        by_role[str(row["role"])][key] += 1
    for role, counts in by_role.items():
        if counts["real"] != counts["synthetic"]:
            raise ValueError(f"role {role} is not class balanced: {counts}")

    return {
        "rows": len(rows),
        "roles": dict(by_role),
        "fit_generators": sorted(fit_generators, key=lambda g: AI_GENBENCH_GENERATORS[g]),
        "ood_generators": sorted(ood_test_generators, key=lambda g: AI_GENBENCH_GENERATORS[g]),
    }


def build_manifest(
    dataset_path: str | Path,
    out_csv: str | Path,
    *,
    fit_per_generator: int = 500,
    calibration_per_generator: int = 125,
    iid_test_per_generator: int = 125,
    ood_per_generator: int = 500,
    ood_generators: Sequence[str] = DEFAULT_OOD_GENERATORS,
    seed: int = DEFAULT_SEED,
) -> dict:
    """Build a leakage-resistant, generator-aware pilot manifest.

    Synthetic examples are balanced per generator. Real examples are balanced
    across their origin datasets using deterministic round-robin selection.
    Fit uses the AI-GenBench train split; calibration/IID/OOD evaluation use
    disjoint rows from the validation split. The OOD generators are never used
    for fit.
    """
    try:
        from datasets import DatasetDict, load_from_disk
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("install MFLab with the second-classifier extras") from exc

    ds = load_from_disk(str(dataset_path))
    if not isinstance(ds, DatasetDict) or "train" not in ds or "validation" not in ds:
        raise ValueError("expected an AI-GenBench DatasetDict with train and validation splits")

    train_rows = _metadata_rows(ds["train"], "train")
    val_rows = _metadata_rows(ds["validation"], "validation")

    ood = tuple(ood_generators)
    unknown = [g for g in ood if g not in AI_GENBENCH_GENERATORS]
    if unknown:
        raise ValueError(f"unknown OOD generators: {unknown}")
    seen = tuple(g for g in AI_GENBENCH_GENERATORS if g not in set(ood))

    manifest: list[dict] = []
    manifest.extend(
        _select_synthetic(
            train_rows,
            seen,
            fit_per_generator,
            seed,
            "fit-synthetic",
            "fit",
            "seen",
            ranks=True,
        )
    )

    train_real_rows = [r for r in train_rows if int(r["label"]) == 0]
    fit_real_idx = _round_robin_balanced_indices(
        train_real_rows, len(seen) * fit_per_generator, seed, "fit-real"
    )
    train_real_by_idx = {int(r["row_index"]): r for r in train_real_rows}
    for rank, idx in enumerate(fit_real_idx, 1):
        manifest.append(_manifest_row(train_real_by_idx[idx], "fit", "real", rank))

    # For seen generators, calibration and IID test are disjoint slices of the
    # same deterministic per-generator ordering within the validation split.
    manifest.extend(
        _select_synthetic(
            val_rows,
            seen,
            calibration_per_generator,
            seed,
            "seen-validation",
            "calibration",
            "seen",
            offset_per_generator=0,
        )
    )
    manifest.extend(
        _select_synthetic(
            val_rows,
            seen,
            iid_test_per_generator,
            seed,
            "seen-validation",
            "iid_test",
            "seen",
            offset_per_generator=calibration_per_generator,
        )
    )
    manifest.extend(
        _select_synthetic(
            val_rows,
            ood,
            ood_per_generator,
            seed,
            "ood-validation",
            "ood_test",
            "ood",
        )
    )

    val_real_rows = [r for r in val_rows if int(r["label"]) == 0]
    # Reserve real validation rows jointly first, then split them so no real
    # control image appears in more than one evaluation role.
    n_cal = len(seen) * calibration_per_generator
    n_iid = len(seen) * iid_test_per_generator
    n_ood = len(ood) * ood_per_generator
    all_real_idx = _round_robin_balanced_indices(
        val_real_rows, n_cal + n_iid + n_ood, seed, "validation-real"
    )
    val_real_by_idx = {int(r["row_index"]): r for r in val_real_rows}
    cursor = 0
    for role, n in (("calibration", n_cal), ("iid_test", n_iid), ("ood_test", n_ood)):
        for idx in all_real_idx[cursor : cursor + n]:
            manifest.append(_manifest_row(val_real_by_idx[idx], role, "real"))
        cursor += n

    summary = _validate_manifest_rows(manifest, ood)
    summary.update(
        {
            "protocol": "MFLAB-SCI-AIGENBENCH-SECOND-0.1",
            "dataset_path": str(Path(dataset_path)),
            "seed": int(seed),
            "fit_per_generator": int(fit_per_generator),
            "calibration_per_generator": int(calibration_per_generator),
            "iid_test_per_generator": int(iid_test_per_generator),
            "ood_per_generator": int(ood_per_generator),
            "default_backbone": DEFAULT_BACKBONE,
        }
    )

    out = Path(out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    role_order = {"fit": 0, "calibration": 1, "iid_test": 2, "ood_test": 3}
    manifest.sort(
        key=lambda r: (
            role_order[str(r["role"])],
            int(r["label"]),
            AI_GENBENCH_GENERATORS.get(str(r["generator"]), "0000"),
            int(r["row_index"]),
        )
    )
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(manifest)
    summary_path = out.with_suffix(out.suffix + ".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def _read_manifest(path: str | Path) -> list[dict]:
    rows: list[dict] = []
    with Path(path).open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["row_index"] = int(row["row_index"])
            row["label"] = int(row["label"])
            row["sample_rank"] = int(row["sample_rank"]) if row.get("sample_rank") else 0
            rows.append(row)
    return rows


def extract_embeddings(
    dataset_path: str | Path,
    manifest_csv: str | Path,
    out_npz: str | Path,
    *,
    backbone: str = DEFAULT_BACKBONE,
    batch_size: int = 32,
    device: str = "auto",
) -> dict:
    """Extract and cache frozen DINOv2 CLS embeddings for manifest rows."""
    try:
        import torch
        from datasets import load_from_disk
        from transformers import AutoImageProcessor, AutoModel
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("install MFLab with the second-classifier extras") from exc

    rows = _read_manifest(manifest_csv)
    ds = load_from_disk(str(dataset_path))
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    processor = AutoImageProcessor.from_pretrained(backbone)
    model = AutoModel.from_pretrained(backbone).to(device)
    model.eval()
    model.requires_grad_(False)

    features: list[np.ndarray] = [None] * len(rows)  # type: ignore[list-item]
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for pos, row in enumerate(rows):
        grouped[str(row["source_split"])].append((pos, row))

    for split_name, items in grouped.items():
        split = ds[split_name]
        for start in range(0, len(items), batch_size):
            batch_items = items[start : start + batch_size]
            indices = [int(row["row_index"]) for _, row in batch_items]
            images = split[indices]["image"]
            inputs = processor(images=images, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.inference_mode():
                output = model(**inputs)
                embedding = output.last_hidden_state[:, 0, :]
            array = embedding.detach().cpu().float().numpy()
            for j, (pos, _) in enumerate(batch_items):
                features[pos] = array[j]

    X = np.asarray(features, dtype=np.float32)
    metadata = {
        "protocol": "MFLAB-SCI-AIGENBENCH-SECOND-0.1",
        "backbone": backbone,
        "embedding_dim": int(X.shape[1]),
        "input_manifest": str(Path(manifest_csv)),
        "rows": int(len(rows)),
        "device_used": device,
    }
    out = Path(out_npz)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out,
        X=X,
        y=np.asarray([int(r["label"]) for r in rows], dtype=np.int8),
        role=np.asarray([str(r["role"]) for r in rows], dtype="U16"),
        generator=np.asarray([str(r["generator"]) for r in rows], dtype="U64"),
        origin_dataset=np.asarray([str(r["origin_dataset"]) for r in rows], dtype="U64"),
        sample_id=np.asarray([str(r["sample_id"]) for r in rows], dtype="U64"),
        sample_rank=np.asarray([int(r["sample_rank"]) for r in rows], dtype=np.int32),
        metadata=np.asarray(json.dumps(metadata), dtype="U4096"),
    )
    return metadata


def _classification_metrics(y: np.ndarray, pred: np.ndarray, score: np.ndarray) -> dict:
    from sklearn.metrics import (
        accuracy_score,
        average_precision_score,
        balanced_accuracy_score,
        brier_score_loss,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "sensitivity": float(recall_score(y, pred, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else None,
        "fpr": float(fp / (fp + tn)) if fp + tn else None,
        "fnr": float(fn / (fn + tp)) if fn + tp else None,
        "f1": float(f1_score(y, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, score)) if len(np.unique(y)) == 2 else None,
        "pr_auc": float(average_precision_score(y, score)) if len(np.unique(y)) == 2 else None,
        "brier": float(brier_score_loss(y, score)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def _wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total <= 0:
        return None
    p = successes / total
    den = 1.0 + z * z / total
    center = (p + z * z / (2 * total)) / den
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / den
    return [max(0.0, center - half), min(1.0, center + half)]


def _add_intervals(metrics: dict) -> dict:
    out = dict(metrics)
    cm = out["confusion_matrix"]
    out["sensitivity_ci95_wilson"] = _wilson(cm["tp"], cm["tp"] + cm["fn"])
    out["specificity_ci95_wilson"] = _wilson(cm["tn"], cm["tn"] + cm["fp"])
    return out


def _fit_stage(
    X: np.ndarray,
    y: np.ndarray,
    role: np.ndarray,
    generator: np.ndarray,
    sample_rank: np.ndarray,
    stage_per_generator: int,
    seed: int,
):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    seen_generators = sorted(
        set(generator[(role == "fit") & (y == 1)].tolist()),
        key=lambda g: AI_GENBENCH_GENERATORS[str(g)],
    )
    synth_fit = (role == "fit") & (y == 1) & (sample_rank <= stage_per_generator)
    real_limit = stage_per_generator * len(seen_generators)
    real_fit = (role == "fit") & (y == 0) & (sample_rank <= real_limit)
    fit_mask = synth_fit | real_fit

    head = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "logreg",
                LogisticRegression(
                    C=1.0,
                    solver="lbfgs",
                    max_iter=2000,
                    random_state=seed,
                ),
            ),
        ]
    )
    head.fit(X[fit_mask], y[fit_mask])

    # Platt calibration on a disjoint role. Logistic regression is already
    # probabilistic, but this explicit one-dimensional calibration step keeps
    # score calibration separate from fitting the decision boundary.
    cal_mask = role == "calibration"
    raw_cal = head.decision_function(X[cal_mask]).reshape(-1, 1)
    platt = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000, random_state=seed)
    platt.fit(raw_cal, y[cal_mask])
    return head, platt, fit_mask


def _score(head, platt, X: np.ndarray) -> np.ndarray:
    raw = head.decision_function(X).reshape(-1, 1)
    return platt.predict_proba(raw)[:, 1]


def _evaluate_role(head, platt, X, y, role, role_name: str) -> dict:
    mask = role == role_name
    score = _score(head, platt, X[mask])
    pred = (score >= 0.5).astype(np.int8)
    return _add_intervals(_classification_metrics(y[mask], pred, score))


def train_head(
    embeddings_npz: str | Path,
    model_out: str | Path,
    result_out: str | Path,
    *,
    learning_curve: Iterable[int] = (125, 250, 500),
    seed: int = DEFAULT_SEED,
    model_name: str = DEFAULT_MODEL_NAME,
) -> dict:
    """Train a calibrated linear probe and report IID + generator-OOD metrics."""
    import joblib
    import sklearn

    data = np.load(embeddings_npz, allow_pickle=False)
    X = data["X"].astype(np.float64)
    y = data["y"].astype(np.int8)
    role = data["role"].astype("U16")
    generator = data["generator"].astype("U64")
    sample_rank = data["sample_rank"].astype(np.int32)
    source_meta = json.loads(str(data["metadata"].item()))

    max_rank = int(sample_rank[(role == "fit") & (y == 1)].max())
    stages = sorted({int(x) for x in learning_curve if int(x) > 0 and int(x) <= max_rank})
    if not stages:
        stages = [max_rank]
    if stages[-1] != max_rank:
        stages.append(max_rank)

    curves: list[dict] = []
    final_head = final_platt = final_fit_mask = None
    for stage in stages:
        head, platt, fit_mask = _fit_stage(X, y, role, generator, sample_rank, stage, seed)
        row = {
            "fit_per_seen_generator": int(stage),
            "fit_count": int(np.sum(fit_mask)),
            "iid_test": _evaluate_role(head, platt, X, y, role, "iid_test"),
            "ood_test": _evaluate_role(head, platt, X, y, role, "ood_test"),
        }
        curves.append(row)
        final_head, final_platt, final_fit_mask = head, platt, fit_mask

    assert final_head is not None and final_platt is not None and final_fit_mask is not None
    seen_generators = sorted(
        set(generator[(role == "fit") & (y == 1)].tolist()),
        key=lambda g: AI_GENBENCH_GENERATORS[str(g)],
    )
    ood_generators = sorted(
        set(generator[(role == "ood_test") & (y == 1)].tolist()),
        key=lambda g: AI_GENBENCH_GENERATORS[str(g)],
    )
    bundle = {
        "model_name": model_name,
        "architecture": "frozen DINOv2 CLS embedding + StandardScaler + LogisticRegression + Platt calibration",
        "backbone": source_meta.get("backbone", DEFAULT_BACKBONE),
        "embedding_dim": int(X.shape[1]),
        "head": final_head,
        "platt_calibrator": final_platt,
        "decision_threshold": 0.5,
        "positive_class": "synthetic",
        "negative_class": "real",
        "scientific_status": "pilot_internal_aigenbench",
        "validated": False,
        "validation_note": (
            "Internal AI-GenBench IID/OOD pilot only. External validation on held-out datasets is required "
            "before promoting this model beyond screening."
        ),
        "seen_generators": seen_generators,
        "ood_generators": ood_generators,
        "sklearn_version": sklearn.__version__,
    }
    model_path = Path(model_out)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path, compress=9)

    result = {
        "protocol": "MFLAB-SCI-AIGENBENCH-SECOND-0.1",
        "model": {
            "name": model_name,
            "backbone": bundle["backbone"],
            "embedding_dim": bundle["embedding_dim"],
            "decision_threshold": 0.5,
            "scientific_status": bundle["scientific_status"],
            "validated": False,
        },
        "splits": {
            "fit": int(np.sum(role == "fit")),
            "calibration": int(np.sum(role == "calibration")),
            "iid_test": int(np.sum(role == "iid_test")),
            "ood_test": int(np.sum(role == "ood_test")),
            "seen_generators": seen_generators,
            "ood_generators": ood_generators,
        },
        "learning_curve": curves,
        "final_iid_test": curves[-1]["iid_test"],
        "final_ood_test": curves[-1]["ood_test"],
        "policy": {
            "no_generator_leakage_to_ood": True,
            "calibration_disjoint_from_fit": True,
            "external_validation_required": True,
            "evidentiary_use": "screening_only",
        },
    }
    result_path = Path(result_out)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="MFLab second synthetic-image classifier research pipeline")
    sub = p.add_subparsers(dest="command", required=True)

    m = sub.add_parser("build-manifest", help="build a generator-aware AI-GenBench pilot manifest")
    m.add_argument("--dataset-path", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--fit-per-generator", type=int, default=500)
    m.add_argument("--calibration-per-generator", type=int, default=125)
    m.add_argument("--iid-test-per-generator", type=int, default=125)
    m.add_argument("--ood-per-generator", type=int, default=500)
    m.add_argument("--seed", type=int, default=DEFAULT_SEED)
    m.add_argument("--ood-generators", nargs="*", default=list(DEFAULT_OOD_GENERATORS))

    e = sub.add_parser("extract-embeddings", help="cache frozen DINOv2 embeddings")
    e.add_argument("--dataset-path", required=True)
    e.add_argument("--manifest", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--backbone", default=DEFAULT_BACKBONE)
    e.add_argument("--batch-size", type=int, default=32)
    e.add_argument("--device", default="auto")

    t = sub.add_parser("train-head", help="train/calibrate linear probe and evaluate IID/OOD")
    t.add_argument("--embeddings", required=True)
    t.add_argument("--model-out", required=True)
    t.add_argument("--result-out", required=True)
    t.add_argument("--learning-curve", default="125,250,500")
    t.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "build-manifest":
        result = build_manifest(
            args.dataset_path,
            args.out,
            fit_per_generator=args.fit_per_generator,
            calibration_per_generator=args.calibration_per_generator,
            iid_test_per_generator=args.iid_test_per_generator,
            ood_per_generator=args.ood_per_generator,
            ood_generators=args.ood_generators,
            seed=args.seed,
        )
    elif args.command == "extract-embeddings":
        result = extract_embeddings(
            args.dataset_path,
            args.manifest,
            args.out,
            backbone=args.backbone,
            batch_size=args.batch_size,
            device=args.device,
        )
    elif args.command == "train-head":
        stages = [int(x.strip()) for x in args.learning_curve.split(",") if x.strip()]
        result = train_head(
            args.embeddings,
            args.model_out,
            args.result_out,
            learning_curve=stages,
            seed=args.seed,
        )
    else:  # pragma: no cover
        raise AssertionError(args.command)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
