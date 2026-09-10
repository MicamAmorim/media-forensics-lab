from __future__ import annotations

import json

import numpy as np
import pytest

from mf_lab.training.second_classifier import (
    DEFAULT_OOD_GENERATORS,
    _round_robin_balanced_indices,
    _validate_manifest_rows,
    train_head,
)


def test_default_ood_window_is_latest_four_generators():
    assert DEFAULT_OOD_GENERATORS == (
        "Stable Diffusion XL 1.0",
        "DALL-E 3",
        "FLUX 1 Dev",
        "FLUX 1 Schnell",
    )


def test_real_sampler_is_deterministic_balanced_and_without_replacement():
    rows = []
    for origin, count in (("A", 10), ("B", 10), ("C", 2)):
        for i in range(count):
            rows.append({"row_index": len(rows), "origin_dataset": origin})

    first = _round_robin_balanced_indices(rows, total=12, seed=123, salt="test")
    second = _round_robin_balanced_indices(rows, total=12, seed=123, salt="test")
    assert first == second
    assert len(first) == len(set(first)) == 12

    origin_by_index = {int(r["row_index"]): r["origin_dataset"] for r in rows}
    counts = {name: sum(origin_by_index[i] == name for i in first) for name in ("A", "B", "C")}
    assert counts["C"] == 2
    assert abs(counts["A"] - counts["B"]) <= 1


def _row(sample_id: str, role: str, label: int, generator: str) -> dict:
    return {
        "sample_id": sample_id,
        "role": role,
        "label": label,
        "generator": generator,
    }


def test_manifest_validation_accepts_balanced_generator_ood_split():
    rows = [
        _row("train:1", "fit", 1, "CycleGAN"),
        _row("train:2", "fit", 0, "(Real)"),
        _row("validation:1", "calibration", 1, "CycleGAN"),
        _row("validation:2", "calibration", 0, "(Real)"),
        _row("validation:3", "iid_test", 1, "CycleGAN"),
        _row("validation:4", "iid_test", 0, "(Real)"),
        _row("validation:5", "ood_test", 1, "FLUX 1 Schnell"),
        _row("validation:6", "ood_test", 0, "(Real)"),
    ]
    summary = _validate_manifest_rows(rows, ["FLUX 1 Schnell"])
    assert summary["rows"] == 8
    assert summary["roles"]["ood_test"] == {"real": 1, "synthetic": 1}


def test_manifest_validation_rejects_generator_leakage():
    rows = [
        _row("train:1", "fit", 1, "FLUX 1 Schnell"),
        _row("train:2", "fit", 0, "(Real)"),
        _row("validation:1", "ood_test", 1, "FLUX 1 Schnell"),
        _row("validation:2", "ood_test", 0, "(Real)"),
    ]
    with pytest.raises(ValueError, match="generator leakage"):
        _validate_manifest_rows(rows, ["FLUX 1 Schnell"])


def test_train_head_smoke_with_disjoint_iid_and_ood_roles(tmp_path):
    rng = np.random.default_rng(7)
    X, y, role, generator, rank = [], [], [], [], []

    def add(n, label, role_name, generator_name, center, ranks=None):
        for i in range(n):
            X.append(rng.normal(center, 0.25, size=6))
            y.append(label)
            role.append(role_name)
            generator.append(generator_name)
            rank.append((ranks[i] if ranks is not None else 0))

    # Fit: two seen generators, four synthetic rows each and eight real controls.
    add(4, 1, "fit", "CycleGAN", 2.0, [1, 2, 3, 4])
    add(4, 1, "fit", "BigGAN", 2.0, [1, 2, 3, 4])
    add(8, 0, "fit", "(Real)", -2.0, list(range(1, 9)))

    # Disjoint calibration, IID and generator-OOD controls.
    add(2, 1, "calibration", "CycleGAN", 1.8)
    add(2, 1, "calibration", "BigGAN", 1.8)
    add(4, 0, "calibration", "(Real)", -1.8)
    add(2, 1, "iid_test", "CycleGAN", 1.7)
    add(2, 1, "iid_test", "BigGAN", 1.7)
    add(4, 0, "iid_test", "(Real)", -1.7)
    add(4, 1, "ood_test", "FLUX 1 Schnell", 1.3)
    add(4, 0, "ood_test", "(Real)", -1.7)

    embeddings = tmp_path / "embeddings.npz"
    np.savez_compressed(
        embeddings,
        X=np.asarray(X, dtype=np.float32),
        y=np.asarray(y, dtype=np.int8),
        role=np.asarray(role, dtype="U16"),
        generator=np.asarray(generator, dtype="U64"),
        origin_dataset=np.asarray(["mock"] * len(y), dtype="U64"),
        sample_id=np.asarray([f"mock:{i}" for i in range(len(y))], dtype="U64"),
        sample_rank=np.asarray(rank, dtype=np.int32),
        metadata=np.asarray(json.dumps({"backbone": "mock-dinov2"}), dtype="U4096"),
    )

    model_out = tmp_path / "head.joblib"
    result_out = tmp_path / "result.json"
    result = train_head(
        embeddings,
        model_out,
        result_out,
        learning_curve=(2, 4),
        seed=7,
    )

    assert model_out.is_file()
    assert result_out.is_file()
    assert [x["fit_per_seen_generator"] for x in result["learning_curve"]] == [2, 4]
    assert result["final_iid_test"]["n"] == 8
    assert result["final_ood_test"]["n"] == 8
    assert result["policy"]["evidentiary_use"] == "screening_only"
