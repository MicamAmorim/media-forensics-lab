from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np


DEVELOPMENT_SEED = 20260908
FRESH_HOLDOUT_SEED = 20260909


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


def _load_rows(parquet_path: str | Path, split_name: str):
    import pyarrow.parquet as pq

    table = pq.read_table(parquet_path, columns=["image", "label"])
    source_labels = np.asarray(table["label"].to_numpy(), dtype=np.int8)
    # CIFAKE mirror: source 0=FAKE, source 1=REAL.
    # MFLab convention: 1=synthetic, 0=real.
    y = (source_labels == 0).astype(np.int8)
    image_col = table["image"]
    rows = []
    for idx in range(len(table)):
        rows.append((
            f"{split_name}:{idx}",
            split_name,
            int(y[idx]),
            int(source_labels[idx]),
            _image_bytes(image_col[idx]),
        ))
    return rows, {
        "rows_total": int(len(table)),
        "real": int(np.sum(y == 0)),
        "synthetic": int(np.sum(y == 1)),
    }


def _worker(payload):
    sample_id, split_name, label, source_label, raw = payload
    from mf_lab.analysis.synthetic_features import extract_synthetic_feature_bank

    fd, tmp = tempfile.mkstemp(prefix="mflab-cifake-", suffix=".img")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        result = extract_synthetic_feature_bank(tmp)
        if result.get("status") != "success":
            raise RuntimeError(f"feature extraction failed: {result}")
        features = {k: float(v) for k, v in (result.get("features") or {}).items()}
        return sample_id, split_name, int(label), int(source_label), features
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def cmd_extract(args) -> None:
    started = time.time()
    train_rows, train_meta = _load_rows(args.train_parquet, "train")
    test_rows, test_meta = _load_rows(args.test_parquet, "test")
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
        for i, row in enumerate(ex.map(_worker, shard_rows, chunksize=32), 1):
            results.append(row)
            if i % 1000 == 0:
                print(json.dumps({
                    "event": "progress",
                    "shard": args.shard,
                    "done": i,
                    "total": len(shard_rows),
                    "elapsed_s": round(time.time() - started, 1),
                }))

    feature_names = sorted(results[0][4])
    for sample_id, _, _, _, feat in results:
        if sorted(feat) != feature_names:
            raise RuntimeError(f"feature schema mismatch at {sample_id}")

    X = np.asarray([[feat[n] for n in feature_names] for _, _, _, _, feat in results], dtype=np.float32)
    y = np.asarray([label for _, _, label, _, _ in results], dtype=np.int8)
    source_y = np.asarray([source_label for _, _, _, source_label, _ in results], dtype=np.int8)
    split = np.asarray([0 if split_name == "train" else 1 for _, split_name, _, _, _ in results], dtype=np.int8)
    ids = np.asarray([sample_id for sample_id, _, _, _, _ in results], dtype="U40")
    meta = {
        "dataset": "CIFAKE",
        "source": "dragonintelligence/CIFAKE-image-dataset",
        "label_mapping": {"source_0": "FAKE -> mflab 1 synthetic", "source_1": "REAL -> mflab 0 real"},
        "train": train_meta,
        "test": test_meta,
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
        source_y=source_y,
        split=split,
        ids=ids,
        feature_names=np.asarray(feature_names, dtype="U128"),
        metadata=np.asarray(json.dumps(meta), dtype="U8192"),
    )
    print(json.dumps({"event": "extract_complete", "out": str(out), "shape": list(X.shape), "elapsed_s": round(time.time() - started, 1)}))


def _source_index(sample_id: str) -> int:
    return int(sample_id.split(":", 1)[1])


def _development_indices(source_labels: np.ndarray, sample_ids: list[str], per_class: int = 10000) -> set[int]:
    """Reconstruct the exact v0.8 development subset previously inspected.

    This allows v0.9 to reserve a fresh holdout from the complement rather than
    claiming the already-inspected official CIFAKE test set as untouched.
    """
    index_by_source_row = {_source_index(sid): i for i, sid in enumerate(sample_ids)}
    rng = np.random.default_rng(DEVELOPMENT_SEED)
    selected: set[int] = set()
    for source_label in (0, 1):
        rows = np.asarray(sorted(
            _source_index(sample_ids[i]) for i in range(len(sample_ids)) if source_labels[i] == source_label
        ), dtype=int)
        chosen = rng.choice(rows, size=per_class, replace=False)
        selected.update(index_by_source_row[int(x)] for x in chosen)
    return selected


def _fresh_holdout_indices(source_labels: np.ndarray, sample_ids: list[str], development: set[int], per_class: int = 5000) -> set[int]:
    rng = np.random.default_rng(FRESH_HOLDOUT_SEED)
    selected: set[int] = set()
    for source_label in (0, 1):
        candidates = np.asarray([
            i for i in range(len(sample_ids))
            if source_labels[i] == source_label and i not in development
        ], dtype=int)
        chosen = rng.choice(candidates, size=per_class, replace=False)
        selected.update(int(x) for x in chosen)
    return selected


def _metrics(y, pred, score=None) -> dict:
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
    result = {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall_sensitivity": float(recall_score(y, pred, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else None,
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else None,
        "f1": float(f1_score(y, pred, zero_division=0)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }
    if score is not None and len(np.unique(y)) == 2:
        result["roc_auc"] = float(roc_auc_score(y, score))
        result["pr_auc"] = float(average_precision_score(y, score))
        result["brier_score"] = float(brier_score_loss(y, score))
    else:
        result["roc_auc"] = None
        result["pr_auc"] = None
        result["brier_score"] = None
    return result


def _wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total <= 0:
        return None
    p = successes / total
    den = 1.0 + z * z / total
    center = (p + z * z / (2 * total)) / den
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / den
    return [max(0.0, center - half), min(1.0, center + half)]


def _with_intervals(metrics: dict) -> dict:
    out = dict(metrics)
    cm = out["confusion_matrix"]
    tn, fp, fn, tp = (cm[k] for k in ("tn", "fp", "fn", "tp"))
    out["accuracy_ci95_wilson"] = _wilson(tn + tp, tn + fp + fn + tp)
    out["sensitivity_ci95_wilson"] = _wilson(tp, tp + fn)
    out["specificity_ci95_wilson"] = _wilson(tn, tn + fp)
    out["false_positive_rate_ci95_wilson"] = _wilson(fp, fp + tn)
    return out


def _fit_hgb_calibrated(X, y, seed: int):
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import HistGradientBoostingClassifier

    base = HistGradientBoostingClassifier(random_state=seed)
    model = CalibratedClassifierCV(base, method="sigmoid", cv=5)
    model.fit(X, y)
    return model


def _fit_hgb(X, y, seed: int):
    from sklearn.ensemble import HistGradientBoostingClassifier

    model = HistGradientBoostingClassifier(random_state=seed)
    model.fit(X, y)
    return model


def _evaluate(model, X, y) -> tuple[dict, np.ndarray, np.ndarray]:
    pred = model.predict(X)
    score = model.predict_proba(X)[:, 1] if hasattr(model, "predict_proba") else None
    return _with_intervals(_metrics(y, pred, score)), pred, score


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_graphs(y, pred, score, out_dir: Path) -> None:
    import matplotlib.pyplot as plt
    from sklearn.calibration import CalibrationDisplay
    from sklearn.metrics import ConfusionMatrixDisplay, PrecisionRecallDisplay, RocCurveDisplay

    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 5))
    RocCurveDisplay.from_predictions(y, score, ax=ax, name="MFLab CIFAKE HGB")
    ax.set_title("ROC — holdout CIFAKE fresco")
    fig.tight_layout()
    fig.savefig(out_dir / "cifake_roc.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    PrecisionRecallDisplay.from_predictions(y, score, ax=ax, name="MFLab CIFAKE HGB")
    ax.set_title("Precision–Recall — holdout CIFAKE fresco")
    fig.tight_layout()
    fig.savefig(out_dir / "cifake_pr.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay.from_predictions(y, pred, display_labels=["real", "synthetic"], values_format="d", ax=ax)
    ax.set_title("Matriz de confusão — holdout CIFAKE fresco")
    fig.tight_layout()
    fig.savefig(out_dir / "cifake_confusion.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    CalibrationDisplay.from_predictions(y, score, n_bins=10, strategy="quantile", ax=ax, name="MFLab CIFAKE HGB")
    ax.set_title("Calibração — holdout CIFAKE fresco")
    fig.tight_layout()
    fig.savefig(out_dir / "cifake_calibration.png", dpi=160)
    plt.close(fig)


def _fmt_pct(x) -> str:
    return "—" if x is None else f"{100.0 * float(x):.2f}%"


def _markdown(result: dict) -> str:
    p = result["primary_fresh_holdout"]
    s = result["secondary_official_test"]
    cm = p["metrics"]["confusion_matrix"]
    return f"""# MFLab v0.9 — validação CIFAKE do classificador embarcado

- **Protocolo:** `{result['protocol']}`
- **Modelo:** `{result['model']['name']}`
- **Feature bank:** `{result['model']['feature_bank']}` ({result['model']['feature_count']} features)
- **Treino final:** {result['splits']['fit_count']:,} imagens CIFAKE
- **Holdout primário fresco:** {result['splits']['fresh_holdout_count']:,} imagens do train original, escolhidas fora do subconjunto de desenvolvimento já inspecionado na v0.8
- **Teste oficial CIFAKE:** {result['splits']['official_test_count']:,} imagens, reportado como avaliação secundária porque já havia sido inspecionado durante o desenvolvimento da v0.8

## Resultado primário — holdout fresco

| Métrica | Resultado |
|---|---:|
| Accuracy | {_fmt_pct(p['metrics']['accuracy'])} |
| Sensibilidade | {_fmt_pct(p['metrics']['recall_sensitivity'])} |
| Especificidade | {_fmt_pct(p['metrics']['specificity'])} |
| FPR | {_fmt_pct(p['metrics']['false_positive_rate'])} |
| ROC-AUC | {p['metrics']['roc_auc']:.6f} |
| PR-AUC | {p['metrics']['pr_auc']:.6f} |
| Brier | {p['metrics']['brier_score']:.6f} |

Matriz de confusão: TN={cm['tn']}, FP={cm['fp']}, FN={cm['fn']}, TP={cm['tp']}.

## Resultado secundário — teste oficial CIFAKE

| Métrica | Resultado |
|---|---:|
| Accuracy | {_fmt_pct(s['metrics']['accuracy'])} |
| Sensibilidade | {_fmt_pct(s['metrics']['recall_sensitivity'])} |
| Especificidade | {_fmt_pct(s['metrics']['specificity'])} |
| FPR | {_fmt_pct(s['metrics']['false_positive_rate'])} |
| ROC-AUC | {s['metrics']['roc_auc']:.6f} |
| PR-AUC | {s['metrics']['pr_auc']:.6f} |

## Limitação de validade

Este modelo é validado **somente no domínio declarado do CIFAKE**: CIFAR-10 real versus Stable Diffusion v1.4, resolução 32×32. Não há, nesta validação, suporte para generalizar as métricas a Midjourney, FLUX, DALL·E, SDXL, outros geradores, screenshots, pós-processamentos, fotografias reais de alta resolução, face swap ou vídeo. O voto `real`/`synthetic` permanece separado de `evidentiary_conclusion`.
"""


def _readme_section(result: dict) -> str:
    p = result["primary_fresh_holdout"]["metrics"]
    s = result["secondary_official_test"]["metrics"]
    model = result["model"]
    return f"""<!-- CIFAKE_V09_START -->
## Classificador automático embarcado e validação CIFAKE — v0.9

A v0.9 inclui o modelo calibrado **`{model['name']}`**, treinado sobre o `synthetic_handcrafted_v2` ({model['feature_count']} features) e embarcado no pacote. O modelo produz um voto computacional `real`/`synthetic` e um score da classe sintética. Esse voto aparece no JSON e no site como **Classificação automática**, mas permanece separado da conclusão pericial `evidentiary_conclusion`.

Para evitar apresentar como "holdout intocado" um conjunto que já havia sido consultado durante o desenvolvimento da v0.8, a validação v0.9 reconstrói o subconjunto de desenvolvimento anterior e reserva, a partir do seu complemento, um **holdout fresco de {result['splits']['fresh_holdout_count']:,} imagens**. O modelo final é ajustado em {result['splits']['fit_count']:,} imagens do train original. O teste oficial de {result['splits']['official_test_count']:,} imagens também é reportado, mas como resultado secundário.

| Avaliação | Accuracy | Sensibilidade | Especificidade | FPR | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| Holdout fresco primário | {_fmt_pct(p['accuracy'])} | {_fmt_pct(p['recall_sensitivity'])} | {_fmt_pct(p['specificity'])} | {_fmt_pct(p['false_positive_rate'])} | {p['roc_auc']:.4f} | {p['pr_auc']:.4f} |
| Teste oficial CIFAKE (secundário) | {_fmt_pct(s['accuracy'])} | {_fmt_pct(s['recall_sensitivity'])} | {_fmt_pct(s['specificity'])} | {_fmt_pct(s['false_positive_rate'])} | {s['roc_auc']:.4f} | {s['pr_auc']:.4f} |

O domínio validado continua estreito: **CIFAR-10 real vs Stable Diffusion v1.4, 32×32**. Para imagens arbitrárias o MFLab ainda gera a classificação automática, mas marca `validated_for_input: false` salvo confirmação explícita do domínio pelo examinador. Isso evita transformar uma boa métrica in-domain em alegação universal de detecção de IA.

![ROC CIFAKE](docs/assets/validation/cifake_roc.png)

![Precision-Recall CIFAKE](docs/assets/validation/cifake_pr.png)

![Matriz de confusão CIFAKE](docs/assets/validation/cifake_confusion.png)

![Calibração CIFAKE](docs/assets/validation/cifake_calibration.png)

Relatório completo: [`validation/scientific/CIFAKE_V09_RESULT.md`](validation/scientific/CIFAKE_V09_RESULT.md). Metadados do modelo: [`mf_lab/models/mflab_cifake_hgb_calibrated_v1.json`](mf_lab/models/mflab_cifake_hgb_calibrated_v1.json).
<!-- CIFAKE_V09_END -->"""


def _update_readme(readme: Path, section: str) -> None:
    text = readme.read_text(encoding="utf-8")
    start = "<!-- CIFAKE_V09_START -->"
    end = "<!-- CIFAKE_V09_END -->"
    if start in text and end in text:
        a = text.index(start)
        b = text.index(end, a) + len(end)
        text = text[:a] + section + text[b:]
    else:
        marker = "## Validação nível 2 — benchmark científico"
        if marker not in text:
            raise RuntimeError("README insertion marker not found")
        text = text.replace(marker, section + "\n\n" + marker, 1)
    readme.write_text(text, encoding="utf-8")


def cmd_train(args) -> None:
    import glob
    import joblib
    import sklearn

    files = sorted(glob.glob(args.features_glob))
    if not files:
        raise FileNotFoundError(f"no feature shards matched {args.features_glob}")
    Xs, ys, source_ys, splits, ids = [], [], [], [], []
    names = None
    for file in files:
        data = np.load(file, allow_pickle=False)
        fn = [str(x) for x in data["feature_names"].tolist()]
        if names is None:
            names = fn
        elif names != fn:
            raise RuntimeError(f"feature schema mismatch in {file}")
        Xs.append(data["X"].astype(np.float64))
        ys.append(data["y"].astype(np.int8))
        source_ys.append(data["source_y"].astype(np.int8))
        splits.append(data["split"].astype(np.int8))
        ids.extend(str(x) for x in data["ids"].tolist())

    X = np.concatenate(Xs)
    y = np.concatenate(ys)
    source_y = np.concatenate(source_ys)
    split = np.concatenate(splits)
    names = names or []

    train_positions = np.flatnonzero(split == 0)
    test_positions = np.flatnonzero(split == 1)
    train_ids = [ids[i] for i in train_positions]
    train_source_y = source_y[train_positions]

    dev_local = _development_indices(train_source_y, train_ids, per_class=10000)
    fresh_local = _fresh_holdout_indices(train_source_y, train_ids, dev_local, per_class=5000)
    fresh_global = np.asarray([train_positions[i] for i in sorted(fresh_local)], dtype=int)
    fit_global = np.asarray([train_positions[i] for i in range(len(train_positions)) if i not in fresh_local], dtype=int)

    Xfit, yfit = X[fit_global], y[fit_global]
    Xfresh, yfresh = X[fresh_global], y[fresh_global]
    Xtest, ytest = X[test_positions], y[test_positions]

    if len(set(fit_global) & set(fresh_global)):
        raise RuntimeError("fit/fresh holdout leakage detected")
    if len(set(fresh_global) & set(test_positions)):
        raise RuntimeError("fresh/test overlap detected")

    model = _fit_hgb_calibrated(Xfit, yfit, args.seed)
    primary_metrics, primary_pred, primary_score = _evaluate(model, Xfresh, yfresh)
    secondary_metrics, _, _ = _evaluate(model, Xtest, ytest)

    autogan_idx = np.asarray([i for i, n in enumerate(names) if n.startswith("autogan_")], dtype=int)
    base_idx = np.asarray([i for i, n in enumerate(names) if not n.startswith("autogan_")], dtype=int)
    ablations = {}
    for key, idx in (("without_autogan", base_idx), ("autogan_only", autogan_idx)):
        m = _fit_hgb(Xfit[:, idx], yfit, args.seed)
        met, _, _ = _evaluate(m, Xfresh[:, idx], yfresh)
        ablations[key] = {"feature_count": int(len(idx)), "metrics": met}

    validation = {
        "protocol": "MFLAB-SCI-CIFAKE-0.2",
        "domain": "CIFAKE: CIFAR-10 real vs Stable Diffusion v1.4 synthetic, 32x32",
        "input_resolution": [32, 32],
        "fit_count": int(len(yfit)),
        "fresh_holdout_count": int(len(yfresh)),
        "official_test_count": int(len(ytest)),
        "development_subset_reconstructed_count": int(len(dev_local)),
        "fresh_holdout_policy": "sampled only from CIFAKE train rows outside the exact v0.8 development subset",
        "seed": args.seed,
        "development_seed": DEVELOPMENT_SEED,
        "fresh_holdout_seed": FRESH_HOLDOUT_SEED,
        "primary_metrics": primary_metrics,
        "secondary_official_test_metrics": secondary_metrics,
    }
    bundle = {
        "feature_names": names,
        "estimator": model,
        "model_name": "mflab_cifake_hgb_calibrated_v1",
        "feature_bank": "synthetic_handcrafted_v2",
        "calibrated": True,
        "validated": True,
        "validation": validation,
        "decision_threshold": 0.5,
        "positive_class": "synthetic",
        "negative_class": "real",
        "sklearn_version": sklearn.__version__,
        "training_note": "Validated only within the declared CIFAKE domain; not a universal AI-image detector.",
    }

    model_out = Path(args.model_out)
    model_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_out, compress=9)
    model_sha = _sha256(model_out)

    result = {
        "protocol": "MFLAB-SCI-CIFAKE-0.2",
        "mflab_version": "0.9.0",
        "mflab_base_sha": args.mflab_base_sha,
        "dataset": {
            "name": "CIFAKE",
            "source": "dragonintelligence/CIFAKE-image-dataset",
            "reference": "Bird & Lotfi, CIFAKE",
            "real_source": "CIFAR-10",
            "synthetic_source": "Stable Diffusion v1.4",
            "resolution": [32, 32],
            "train_parquet_sha256": args.train_sha256,
            "test_parquet_sha256": args.test_sha256,
        },
        "splits": {
            "fit_count": int(len(yfit)),
            "fit_real": int(np.sum(yfit == 0)),
            "fit_synthetic": int(np.sum(yfit == 1)),
            "fresh_holdout_count": int(len(yfresh)),
            "fresh_holdout_real": int(np.sum(yfresh == 0)),
            "fresh_holdout_synthetic": int(np.sum(yfresh == 1)),
            "official_test_count": int(len(ytest)),
            "official_test_real": int(np.sum(ytest == 0)),
            "official_test_synthetic": int(np.sum(ytest == 1)),
            "reconstructed_v08_development_count": int(len(dev_local)),
        },
        "model": {
            "name": bundle["model_name"],
            "estimator": "CalibratedClassifierCV(HistGradientBoostingClassifier, sigmoid, cv=5)",
            "feature_bank": bundle["feature_bank"],
            "feature_count": len(names),
            "decision_threshold": 0.5,
            "calibrated": True,
            "validated": True,
            "model_sha256": model_sha,
            "sklearn_version": sklearn.__version__,
        },
        "primary_fresh_holdout": {"status": "primary", "metrics": primary_metrics},
        "secondary_official_test": {
            "status": "secondary_previously_inspected_during_v08_development",
            "metrics": secondary_metrics,
        },
        "ablations_primary_holdout": ablations,
        "forensic_policy": {
            "automatic_label_is_evidentiary_conclusion": False,
            "default_validated_for_arbitrary_input": False,
            "domain_confirmation_env": "MFLAB_SYNTHETIC_MODEL_DOMAIN_CONFIRMED=1",
        },
        "limitations": [
            "Validation is in-domain for CIFAKE only.",
            "No cross-generator or cross-family validity is established by this experiment.",
            "CIFAKE resolution is 32x32 and does not represent arbitrary high-resolution forensic evidence.",
            "The official CIFAKE test set is reported secondarily because it was already inspected during v0.8 development.",
            "The machine real/synthetic label remains separate from evidentiary_conclusion.",
        ],
    }

    json_out = Path(args.result_json)
    md_out = Path(args.result_markdown)
    sidecar = Path(args.model_metadata)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md_out.write_text(_markdown(result), encoding="utf-8")
    sidecar.write_text(json.dumps({
        "model_name": bundle["model_name"],
        "sha256": model_sha,
        "feature_bank": bundle["feature_bank"],
        "feature_count": len(names),
        "decision_threshold": 0.5,
        "positive_class": "synthetic",
        "negative_class": "real",
        "calibrated": True,
        "validated": True,
        "validation_domain": {
            "dataset": "CIFAKE",
            "real_source": "CIFAR-10",
            "synthetic_source": "Stable Diffusion v1.4",
            "resolution": [32, 32],
            "domain_match_rule": "examiner confirmation required; resolution alone is not sufficient",
        },
        "validation_report": str(json_out).replace("\\", "/"),
        "warning": "Validated only within the declared CIFAKE domain. Arbitrary-image classification is screening unless the domain is explicitly confirmed.",
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    _make_graphs(yfresh, primary_pred, primary_score, Path(args.graph_dir))
    if args.readme:
        _update_readme(Path(args.readme), _readme_section(result))

    print(_markdown(result))
    print(json.dumps({
        "event": "training_complete",
        "model": str(model_out),
        "model_sha256": model_sha,
        "primary_accuracy": primary_metrics["accuracy"],
        "primary_fpr": primary_metrics["false_positive_rate"],
        "secondary_accuracy": secondary_metrics["accuracy"],
    }))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reproducible CIFAKE training/export workflow for the MFLab bundled classifier")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("extract")
    p.add_argument("--train-parquet", required=True)
    p.add_argument("--test-parquet", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--shards", type=int, required=True)
    p.add_argument("--workers", type=int, default=2)
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("train")
    p.add_argument("--features-glob", required=True)
    p.add_argument("--model-out", default="mf_lab/models/mflab_cifake_hgb_calibrated_v1.joblib")
    p.add_argument("--model-metadata", default="mf_lab/models/mflab_cifake_hgb_calibrated_v1.json")
    p.add_argument("--result-json", default="validation/scientific/CIFAKE_V09_RESULT.json")
    p.add_argument("--result-markdown", default="validation/scientific/CIFAKE_V09_RESULT.md")
    p.add_argument("--graph-dir", default="docs/assets/validation")
    p.add_argument("--readme", default="README.md")
    p.add_argument("--seed", type=int, default=20260909)
    p.add_argument("--mflab-base-sha", default="0285b6cfad137db552dfbf8a5158c14d26791822")
    p.add_argument("--train-sha256", default="c906031ad6ac44c7d0fc21e8f9315d85cf351540b6517bd6c0de3ee2f884021b")
    p.add_argument("--test-sha256", default="7767d5285d009471175ac7985c60367d82a34088f29c67185da7af2c53b7975d")
    p.set_defaults(func=cmd_train)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
