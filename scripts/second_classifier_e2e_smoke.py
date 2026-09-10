from __future__ import annotations

import csv
import json
from pathlib import Path

from mf_lab.training import selective_acquisition as sa
from mf_lab.training.second_classifier import DEFAULT_SEED, train_head
from mf_lab.training.selective_embeddings import extract_verified_materialized_embeddings
from mf_lab.training.selective_remote_rows import fetch_generator_quota_rows
from mf_lab.training.stable_real_acquisition_v2 import (
    freeze_materialized_corpus,
    materialize_stable_plan,
)

SEEN = ("CycleGAN", "Stable Diffusion 1.5")
OOD = ("DALL-E 3", "FLUX 1 Schnell")


def _laion_rows(split: str, count: int, *, cache_dir: Path, salt: str) -> list[str]:
    ids = sa.load_official_real_file_ids(split, cache_dir=cache_dir)
    return sa._balanced_file_ids(
        ids,
        count,
        DEFAULT_SEED,
        salt,
        allowed_prefixes=("LAION-400M",),
    )


def main() -> int:
    work = Path("work/second_classifier/e2e-smoke")
    cache = work / "cache"
    plan = work / "plan.csv"
    materialized = work / "materialized.csv"
    frozen = work / "frozen-manifest.csv"
    lock = work / "corpus.lock.json"
    embeddings = work / "dinov2_embeddings.npz"
    model = work / "second_classifier_smoke.joblib"
    result_json = work / "training-result.json"
    report_json = work / "e2e-report.json"
    work.mkdir(parents=True, exist_ok=True)

    train_selected, train_scan = fetch_generator_quota_rows(
        "train",
        {g: 20 for g in SEEN},
        cache_dir=cache,
        seed=DEFAULT_SEED,
        request_delay_seconds=0.75,
    )
    validation_selected, val_scan = fetch_generator_quota_rows(
        "validation",
        {SEEN[0]: 10, SEEN[1]: 10, OOD[0]: 10, OOD[1]: 10},
        cache_dir=cache,
        seed=DEFAULT_SEED,
        request_delay_seconds=0.75,
    )

    rows: list[dict] = []
    for generator in SEEN:
        for rank, row in enumerate(train_selected[generator], 1):
            rows.append(sa._fake_manifest_row(row, "fit", "seen", rank))

    for generator in SEEN:
        selected = validation_selected[generator]
        for row in selected[:5]:
            rows.append(sa._fake_manifest_row(row, "calibration", "seen"))
        for row in selected[5:10]:
            rows.append(sa._fake_manifest_row(row, "iid_test", "seen"))

    for generator in OOD:
        for row in validation_selected[generator]:
            rows.append(sa._fake_manifest_row(row, "ood_test", "ood"))

    laion_train_index = sa.load_laion_url_index("train", cache_dir=cache)
    laion_val_index = sa.load_laion_url_index("validation", cache_dir=cache)
    fit_real = _laion_rows("train", 40, cache_dir=cache, salt="e2e-fit-real")
    val_real = _laion_rows("validation", 40, cache_dir=cache, salt="e2e-val-real")

    for rank, file_id in enumerate(fit_real, 1):
        url, kind = sa.resolve_real_url(file_id, laion_index=laion_train_index)
        rows.append(sa._real_manifest_row("train", file_id, "fit", source_url=url, source_kind=kind, rank=rank))

    cursor = 0
    for role, count in (("calibration", 10), ("iid_test", 10), ("ood_test", 20)):
        for file_id in val_real[cursor: cursor + count]:
            url, kind = sa.resolve_real_url(file_id, laion_index=laion_val_index)
            rows.append(sa._real_manifest_row("validation", file_id, role, source_url=url, source_kind=kind))
        cursor += count

    expected = 160
    if len(rows) != expected:
        raise AssertionError(f"e2e smoke expected {expected} rows, got {len(rows)}")

    with plan.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sa.REMOTE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    acquisition = materialize_stable_plan(
        plan,
        work / "images",
        materialized,
        cache_dir=cache,
        diagnostics_out=work / "diagnostics.json",
        replacement_log_out=work / "replacements.json",
        seed=DEFAULT_SEED,
        max_laion_replacements_per_sample=12,
    )
    if acquisition["failed_or_unresolved"] != 0:
        raise RuntimeError(f"e2e acquisition incomplete: {acquisition}")

    corpus = freeze_materialized_corpus(
        materialized,
        frozen,
        lock,
        replacement_log=work / "replacements.json",
    )
    embedding_meta = extract_verified_materialized_embeddings(
        materialized,
        embeddings,
        backbone="facebook/dinov2-small",
        batch_size=16,
        device="cpu",
    )
    training = train_head(
        embeddings,
        model,
        result_json,
        learning_curve=(10, 20),
        seed=DEFAULT_SEED,
        model_name="mflab_second_classifier_e2e_smoke",
    )

    report = {
        "protocol": "MFLAB-SCI-SECOND-CLASSIFIER-E2E-SMOKE-0.1",
        "rows": expected,
        "seen_generators": list(SEEN),
        "ood_generators": list(OOD),
        "scan": {"train": train_scan, "validation": val_scan},
        "acquisition": acquisition,
        "corpus": corpus,
        "embedding": embedding_meta,
        "training": training,
        "success": True,
    }
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
