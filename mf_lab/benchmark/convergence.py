from __future__ import annotations

import csv
import json
import math
import tempfile
from pathlib import Path
from typing import Iterable

from mf_lab.pipeline import analyze_file

REVIEW_LEVELS = {
    "moderate_convergence_for_expert_review",
    "high_convergence_for_expert_review",
}


def _wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total <= 0:
        return None
    p = successes / total
    z2 = z * z
    denominator = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denominator
    margin = (
        z
        * math.sqrt((p * (1.0 - p) / total) + z2 / (4.0 * total * total))
        / denominator
    )
    return [max(0.0, center - margin), min(1.0, center + margin)]


def binary_metrics(rows: Iterable[dict], prediction_key: str) -> dict:
    materialized = list(rows)
    tp = tn = fp = fn = 0
    for row in materialized:
        truth = bool(row["expected_synthetic"])
        pred = bool(row[prediction_key])
        if truth and pred:
            tp += 1
        elif truth and not pred:
            fn += 1
        elif not truth and pred:
            fp += 1
        else:
            tn += 1

    positives = tp + fn
    negatives = tn + fp
    total = positives + negatives

    sensitivity = tp / positives if positives else None
    specificity = tn / negatives if negatives else None
    fpr = fp / negatives if negatives else None
    fnr = fn / positives if positives else None
    precision = tp / (tp + fp) if (tp + fp) else None
    accuracy = (tp + tn) / total if total else None
    balanced_accuracy = (
        (sensitivity + specificity) / 2.0
        if sensitivity is not None and specificity is not None
        else None
    )

    return {
        "sample_count": total,
        "positive_count": positives,
        "negative_count": negatives,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "sensitivity": sensitivity,
        "specificity": specificity,
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
        "precision": precision,
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "sensitivity_wilson_95": _wilson_interval(tp, positives),
        "specificity_wilson_95": _wilson_interval(tn, negatives),
        "warning": (
            "These are descriptive error rates for the supplied labeled sample only. "
            "They do not establish population-level forensic validity or transfer to other generators, cameras, compression histories or domains."
        ),
    }


def _demo_expected_synthetic(meta: dict) -> bool:
    label = str(meta.get("label", "")).strip().lower()
    method = str(meta.get("method", "")).strip().lower()
    return label == "synthetic" or method.startswith("synthetic_")


def _parse_expected_synthetic(value: str) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "synthetic", "deepfake", "ai"}:
        return True
    if normalized in {"0", "false", "no", "real", "non_synthetic", "non-synthetic"}:
        return False
    raise ValueError(f"unsupported expected_synthetic value: {value!r}")


def _prediction_from_report(report: dict) -> tuple[bool, bool, str | None, str | None]:
    methods = report.get("methods") or {}
    fusion = methods.get("synthetic_evidence_fusion") or {}
    protocol = methods.get("deepfake_protocol") or {}
    level = fusion.get("convergence_level")
    fusion_review = level in REVIEW_LEVELS
    triage = protocol.get("triage_assessment")
    protocol_review = triage == "needs_expert_review"
    return fusion_review, protocol_review, level, triage


def _analyze_cases(cases: list[dict]) -> list[dict]:
    rows: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="mflab-convergence-benchmark-") as tmp:
        out = Path(tmp)
        for index, case in enumerate(cases):
            path = Path(case["path"])
            report = analyze_file(path, out / f"case-{index:04d}", profile="full")
            fusion_review, protocol_review, level, triage = _prediction_from_report(report)
            rows.append(
                {
                    "case_id": case.get("case_id") or path.name,
                    "path": str(path),
                    "expected_synthetic": bool(case["expected_synthetic"]),
                    "source": case.get("source"),
                    "fusion_convergence_level": level,
                    "fusion_review": fusion_review,
                    "protocol_triage": triage,
                    "protocol_review": protocol_review,
                }
            )
    return rows


def _demo_cases(dataset_dir: str | Path | None = None) -> tuple[list[dict], str]:
    root = Path(__file__).resolve().parents[2]
    dataset = Path(dataset_dir) if dataset_dir else root / "dataset" / "demo"
    gt = json.loads((dataset / "ground_truth.json").read_text(encoding="utf-8"))
    cases: list[dict] = []
    for name, meta in (gt.get("images") or {}).items():
        cases.append(
            {
                "case_id": name,
                "path": dataset / "images" / name,
                "expected_synthetic": _demo_expected_synthetic(meta),
                "source": "dataset/demo/ground_truth.json",
            }
        )
    return cases, str(dataset)


def _manifest_cases(manifest_path: str | Path) -> tuple[list[dict], str]:
    manifest = Path(manifest_path)
    cases: list[dict] = []
    with manifest.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"path", "expected_synthetic"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"manifest missing columns: {sorted(missing)}")
        for idx, row in enumerate(reader, start=2):
            raw_path = str(row.get("path", "")).strip()
            if not raw_path:
                raise ValueError(f"manifest line {idx}: path is empty")
            path = Path(raw_path)
            if not path.is_absolute():
                path = (manifest.parent / path).resolve()
            if not path.is_file():
                raise FileNotFoundError(f"manifest line {idx}: media not found: {path}")
            cases.append(
                {
                    "case_id": str(row.get("case_id") or path.name),
                    "path": path,
                    "expected_synthetic": _parse_expected_synthetic(row.get("expected_synthetic", "")),
                    "source": row.get("source") or str(manifest),
                }
            )
    if not cases:
        raise ValueError("manifest contains no cases")
    return cases, str(manifest)


def run_convergence_benchmark(
    *,
    dataset_dir: str | Path | None = None,
    manifest_path: str | Path | None = None,
    out_path: str | Path | None = None,
) -> dict:
    """Benchmark review escalation as a binary screening decision on labeled media.

    The benchmark reports both the fusion-only rule (moderate/high convergence)
    and the final protocol review decision. Metrics remain descriptive for the
    supplied sample; no automatic threshold tuning or evidentiary promotion is
    performed.
    """
    if manifest_path is not None:
        cases, source = _manifest_cases(manifest_path)
        benchmark_scope = "external_labeled_manifest_descriptive_benchmark"
    else:
        cases, source = _demo_cases(dataset_dir)
        benchmark_scope = "controlled_demo_pilot_benchmark"

    rows = _analyze_cases(cases)
    result = {
        "schema_version": "0.9.2",
        "protocol": "MFLAB-CONVERGENCE-BENCH-0.1",
        "benchmark_scope": benchmark_scope,
        "source": source,
        "positive_definition": (
            "Media whose ground truth explicitly indicates synthetic content. "
            "For dataset/demo this includes label=synthetic or method beginning with synthetic_."
        ),
        "fusion_positive_definition": sorted(REVIEW_LEVELS),
        "protocol_positive_definition": "triage_assessment == needs_expert_review",
        "sample_count": len(rows),
        "cases": rows,
        "fusion_metrics": binary_metrics(rows, "fusion_review"),
        "protocol_metrics": binary_metrics(rows, "protocol_review"),
        "forensic_validation_claim": False,
        "interpretation": (
            "This benchmark quantifies how often the current review-escalation rules fire on the labeled sample. "
            "It is intentionally separate from model calibration and from the evidentiary conclusion. "
            "No threshold is optimized on these results. Real-world validation requires a larger, generator-diverse, capture-diverse and transformation-diverse locked test corpus."
        ),
    }

    if out_path is not None:
        target = Path(out_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result
