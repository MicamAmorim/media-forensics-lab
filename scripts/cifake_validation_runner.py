from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np


def _image_bytes(cell) -> bytes:
    if cell is None:
        raise ValueError("missing image cell")
    if isinstance(cell, (bytes, bytearray, memoryview)):
        return bytes(cell)
    if isinstance(cell, dict):
        raw = cell.get("bytes")
        if raw is not None:
            return bytes(raw)
        path = cell.get("path")
        if path:
            return Path(path).read_bytes()
    if hasattr(cell, "as_py"):
        return _image_bytes(cell.as_py())
    raise TypeError(f"unsupported image cell type: {type(cell)!r}")


def _sample_indices(labels: np.ndarray, per_class: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    selected = []
    for label in (0, 1):
        idx = np.flatnonzero(labels == label)
        if len(idx) < per_class:
            raise ValueError(f"class {label} has {len(idx)} rows, requested {per_class}")
        if len(idx) == per_class:
            chosen = idx
        else:
            chosen = rng.choice(idx, size=per_class, replace=False)
        selected.extend(int(x) for x in chosen)
    return np.asarray(sorted(selected), dtype=np.int64)


def _load_selected(parquet_path: str | Path, per_class: int, seed: int, split_name: str):
    import pyarrow.parquet as pq

    table = pq.read_table(parquet_path, columns=["image", "label"])
    labels_original = np.asarray(table["label"].to_numpy(), dtype=np.int8)
    labels_mflab = (labels_original == 0).astype(np.int8)
    selected = _sample_indices(labels_original, per_class=per_class, seed=seed)
    image_col = table["image"]
    rows = []
    for idx in selected:
        rows.append((
            f"{split_name}:{int(idx)}",
            split_name,
            int(labels_mflab[idx]),
            _image_bytes(image_col[int(idx)]),
        ))
    return rows, {
        "rows_total": int(len(table)),
        "rows_selected": int(len(rows)),
        "selected_real": int(sum(r[2] == 0 for r in rows)),
        "selected_synthetic": int(sum(r[2] == 1 for r in rows)),
    }


def _worker(payload):
    sample_id, split_name, label, raw = payload
    from mf_lab.analysis.synthetic_features import extract_synthetic_feature_bank

    fd, tmp = tempfile.mkstemp(prefix="mflab-cifake-", suffix=".img")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        result = extract_synthetic_feature_bank(tmp)
        if result.get("status") != "success":
            raise RuntimeError(f"feature extraction failed: {result}")
        features = {k: float(v) for k, v in (result.get("features") or {}).items()}
        return sample_id, split_name, int(label), features
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def cmd_extract(args):
    started = time.time()
    train_rows, train_meta = _load_selected(args.train_parquet, args.train_per_class, args.seed, "train")
    test_rows, test_meta = _load_selected(args.test_parquet, args.test_per_class, args.seed + 1, "test")
    all_rows = train_rows + test_rows
    shard_rows = [row for i, row in enumerate(all_rows) if i % args.shards == args.shard]
    if not shard_rows:
        raise RuntimeError("empty shard")

    workers = max(1, min(args.workers, os.cpu_count() or 1))
    print(json.dumps({
        "event": "extract_start",
        "shard": args.shard,
        "shards": args.shards,
        "rows": len(shard_rows),
        "workers": workers,
        "train": train_meta,
        "test": test_meta,
    }))

    results = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, row in enumerate(ex.map(_worker, shard_rows, chunksize=16), 1):
            results.append(row)
            if i % 500 == 0:
                elapsed = time.time() - started
                print(json.dumps({"event": "progress", "shard": args.shard, "done": i, "total": len(shard_rows), "elapsed_s": round(elapsed, 1)}))

    feature_names = sorted(results[0][3])
    for sample_id, _, _, feat in results:
        if sorted(feat) != feature_names:
            raise RuntimeError(f"feature schema mismatch at {sample_id}")

    X = np.asarray([[feat[n] for n in feature_names] for _, _, _, feat in results], dtype=np.float32)
    y = np.asarray([label for _, _, label, _ in results], dtype=np.int8)
    split = np.asarray([0 if split_name == "train" else 1 for _, split_name, _, _ in results], dtype=np.int8)
    ids = np.asarray([sample_id for sample_id, _, _, _ in results], dtype="U40")
    meta = {
        "dataset": "CIFAKE",
        "source": "dragonintelligence/CIFAKE-image-dataset",
        "label_mapping": {"source_0": "FAKE -> mflab 1 synthetic", "source_1": "REAL -> mflab 0 real"},
        "train": train_meta,
        "test": test_meta,
        "seed": args.seed,
        "shard": args.shard,
        "shards": args.shards,
        "elapsed_seconds": time.time() - started,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out,
        X=X,
        y=y,
        split=split,
        ids=ids,
        feature_names=np.asarray(feature_names, dtype="U128"),
        metadata=np.asarray(json.dumps(meta), dtype="U8192"),
    )
    print(json.dumps({"event": "extract_complete", "out": str(out), "shape": list(X.shape), "elapsed_s": round(time.time() - started, 1)}))


def _wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total <= 0:
        return None
    p = successes / total
    den = 1.0 + z * z / total
    center = (p + z * z / (2 * total)) / den
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / den
    return [max(0.0, center - half), min(1.0, center + half)]


def _augment_intervals(metrics: dict) -> dict:
    m = dict(metrics)
    cm = m.get("confusion_matrix") or {}
    tn, fp, fn, tp = (int(cm.get(k, 0)) for k in ("tn", "fp", "fn", "tp"))
    n = tn + fp + fn + tp
    m["accuracy_ci95_wilson"] = _wilson(tn + tp, n)
    m["sensitivity_ci95_wilson"] = _wilson(tp, tp + fn)
    m["specificity_ci95_wilson"] = _wilson(tn, tn + fp)
    m["false_positive_rate_ci95_wilson"] = _wilson(fp, fp + tn)
    return m


def _evaluate_family(Xtr, ytr, Xte, yte, feature_names, seed: int):
    from sklearn.base import clone
    from mf_lab.benchmark.synthetic import _candidate_estimators, _fit_selected, _metrics, _selection_scores

    estimators = _candidate_estimators(seed)
    selection = _selection_scores(Xtr, ytr, estimators, seed, validation=None)
    best_name = max(selection, key=selection.get)
    best, calibrated = _fit_selected(estimators[best_name], Xtr, ytr)
    pred = best.predict(Xte)
    score = best.predict_proba(Xte)[:, 1] if hasattr(best, "predict_proba") else None
    selected_metrics = _augment_intervals(_metrics(yte, pred, score))
    comparison = {}
    for name, est in estimators.items():
        fitted = clone(est).fit(Xtr, ytr)
        pp = fitted.predict(Xte)
        ss = fitted.predict_proba(Xte)[:, 1] if hasattr(fitted, "predict_proba") else None
        comparison[name] = _augment_intervals(_metrics(yte, pp, ss))
    return {
        "feature_count": int(Xtr.shape[1]),
        "feature_names": list(feature_names),
        "selection_balanced_accuracy_cv": {k: float(v) for k, v in selection.items()},
        "selected_model": best_name,
        "selected_model_calibrated": bool(calibrated),
        "selected_model_metrics": selected_metrics,
        "comparison_on_final_test": comparison,
    }


def _fmt_pct(x):
    return "—" if x is None else f"{100.0 * float(x):.2f}%"


def _fmt_metric(x):
    return "—" if x is None else f"{float(x):.4f}"


def _markdown(result: dict) -> str:
    lines = []
    lines.append("# MFLab v0.8 — validação científica em CIFAKE")
    lines.append("")
    lines.append(f"- **MFLab base SHA:** `{result['mflab_base_sha']}`")
    lines.append("- **Dataset:** CIFAKE (Stable Diffusion v1.4 vs CIFAR-10)")
    lines.append(f"- **Treino usado:** {result['dataset']['train_count']:,} imagens")
    lines.append(f"- **Teste oficial usado:** {result['dataset']['test_count']:,} imagens")
    lines.append(f"- **Total processado:** {result['dataset']['total_count']:,} imagens")
    lines.append("- **Resolução:** 32×32 pixels")
    lines.append("")
    lines.append("## Resultado principal")
    lines.append("")
    lines.append("| Feature set | Modelo selecionado | Accuracy | Sensibilidade | Especificidade | FPR | ROC-AUC | PR-AUC |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for key, label in (("combined", "MFLab v0.8 combinado"), ("base", "MFLab sem AutoGAN"), ("autogan_only", "AutoGAN descriptors somente")):
        row = result["ablations"][key]
        m = row["selected_model_metrics"]
        lines.append(
            f"| {label} | {row['selected_model']} | {_fmt_pct(m.get('accuracy'))} | {_fmt_pct(m.get('recall_sensitivity'))} | {_fmt_pct(m.get('specificity'))} | {_fmt_pct(m.get('false_positive_rate'))} | {_fmt_metric(m.get('roc_auc'))} | {_fmt_metric(m.get('pr_auc'))} |"
        )
    lines.append("")
    cm = result["ablations"]["combined"]["selected_model_metrics"]["confusion_matrix"]
    lines.append("### Matriz de confusão — método combinado")
    lines.append("")
    lines.append(f"- TN (real corretamente real): **{cm['tn']:,}**")
    lines.append(f"- FP (real acusado como sintético): **{cm['fp']:,}**")
    lines.append(f"- FN (sintético perdido): **{cm['fn']:,}**")
    lines.append(f"- TP (sintético detectado): **{cm['tp']:,}**")
    lines.append("")
    lines.append("## Interpretação")
    lines.append("")
    lines.append("Este experimento mede desempenho **dentro do domínio CIFAKE**: imagens reais CIFAR-10 e imagens sintéticas Stable Diffusion v1.4, todas 32×32. Não mede generalização para Midjourney, FLUX, DALL·E, SDXL, face swap ou vídeo. O teste oficial não participou da seleção do modelo; a seleção foi feita por cross-validation estratificada apenas no subconjunto de treino.")
    lines.append("")
    lines.append("Os descritores AutoGAN são avaliados como features espectrais; não há checkpoint ResNet34 AutoGAN configurado neste experimento. Portanto, a comparação `autogan_only` mede os descritores matemáticos AutoGAN-compatible combinados com os classificadores científicos do MFLab, não o checkpoint original do AutoGAN.")
    lines.append("")
    return "\n".join(lines) + "\n"


def cmd_evaluate(args):
    import glob

    files = sorted(glob.glob(args.features_glob))
    if not files:
        raise FileNotFoundError(f"no feature shards matched {args.features_glob}")
    Xs, ys, ss, ids = [], [], [], []
    names = None
    shard_meta = []
    for file in files:
        data = np.load(file, allow_pickle=False)
        f_names = [str(x) for x in data["feature_names"].tolist()]
        if names is None:
            names = f_names
        elif names != f_names:
            raise RuntimeError(f"feature schema mismatch in {file}")
        Xs.append(data["X"].astype(np.float64))
        ys.append(data["y"].astype(np.int8))
        ss.append(data["split"].astype(np.int8))
        ids.extend(str(x) for x in data["ids"].tolist())
        shard_meta.append(json.loads(str(data["metadata"].item())))
    X = np.concatenate(Xs, axis=0)
    y = np.concatenate(ys, axis=0)
    split = np.concatenate(ss, axis=0)
    names = names or []

    train_mask = split == 0
    test_mask = split == 1
    Xtr, ytr = X[train_mask], y[train_mask]
    Xte, yte = X[test_mask], y[test_mask]
    if len(np.unique(ytr)) != 2 or len(np.unique(yte)) != 2:
        raise RuntimeError("both train and test must contain both classes")

    autogan_idx = np.asarray([i for i, n in enumerate(names) if n.startswith("autogan_")], dtype=int)
    base_idx = np.asarray([i for i, n in enumerate(names) if not n.startswith("autogan_")], dtype=int)
    if len(autogan_idx) == 0 or len(base_idx) == 0:
        raise RuntimeError("expected both AutoGAN and base feature families")

    started = time.time()
    combined = _evaluate_family(Xtr, ytr, Xte, yte, names, args.seed)
    base = _evaluate_family(Xtr[:, base_idx], ytr, Xte[:, base_idx], yte, [names[i] for i in base_idx], args.seed)
    autogan_only = _evaluate_family(Xtr[:, autogan_idx], ytr, Xte[:, autogan_idx], yte, [names[i] for i in autogan_idx], args.seed)

    result = {
        "protocol": "MFLAB-SCI-CIFAKE-0.1",
        "mflab_version": "0.8.x",
        "mflab_base_sha": os.environ.get("MFLAB_BASE_SHA", "unknown"),
        "validation_branch_sha": os.environ.get("GITHUB_SHA", "unknown"),
        "dataset": {
            "name": "CIFAKE",
            "source": "dragonintelligence/CIFAKE-image-dataset (Hugging Face mirror)",
            "original_reference": "Bird & Lotfi, CIFAKE",
            "generator": "Stable Diffusion v1.4",
            "real_source": "CIFAR-10",
            "resolution": [32, 32],
            "dataset_size": 120000,
            "train_available": 100000,
            "test_available": 20000,
            "train_count": int(train_mask.sum()),
            "test_count": int(test_mask.sum()),
            "total_count": int(len(y)),
            "train_real": int(np.sum(ytr == 0)),
            "train_synthetic": int(np.sum(ytr == 1)),
            "test_real": int(np.sum(yte == 0)),
            "test_synthetic": int(np.sum(yte == 1)),
            "train_parquet_sha256": "c906031ad6ac44c7d0fc21e8f9315d85cf351540b6517bd6c0de3ee2f884021b",
            "test_parquet_sha256": "7767d5285d009471175ac7985c60367d82a34088f29c67185da7af2c53b7975d",
        },
        "split_policy": "20k stratified deterministic subset of official training split; full official 20k test split; test never used for model selection",
        "seed": args.seed,
        "feature_count_combined": len(names),
        "feature_count_base": int(len(base_idx)),
        "feature_count_autogan": int(len(autogan_idx)),
        "ablations": {
            "combined": combined,
            "base": base,
            "autogan_only": autogan_only,
        },
        "runtime": {
            "evaluation_seconds": time.time() - started,
            "feature_shards": len(files),
            "shard_metadata": shard_meta,
        },
        "limitations": [
            "CIFAKE is single-generator (Stable Diffusion v1.4), so this is an in-domain validation, not cross-generator validation.",
            "All images are 32x32; rescaling inside some MFLab descriptors can amplify dataset-specific low-resolution artifacts.",
            "Real images come from CIFAR-10 and synthetic images from a different generation pipeline; dataset-source confounding may inflate performance.",
            "No AutoGAN ResNet34 checkpoint was configured; only clean-room AutoGAN-compatible spectral descriptors were tested.",
            "Results do not justify a universal forensic probability or evidentiary conclusion for arbitrary AI-generated media.",
        ],
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md = _markdown(result)
    Path(args.markdown).write_text(md, encoding="utf-8")
    print(md)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("extract")
    p.add_argument("--train-parquet", required=True)
    p.add_argument("--test-parquet", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--shards", type=int, required=True)
    p.add_argument("--train-per-class", type=int, default=10000)
    p.add_argument("--test-per-class", type=int, default=10000)
    p.add_argument("--seed", type=int, default=20260908)
    p.add_argument("--workers", type=int, default=2)
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("evaluate")
    p.add_argument("--features-glob", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--markdown", required=True)
    p.add_argument("--seed", type=int, default=20260908)
    p.set_defaults(func=cmd_evaluate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
