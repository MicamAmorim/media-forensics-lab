from __future__ import annotations

import pytest

from mf_lab.training.second_classifier import (
    DEFAULT_OOD_GENERATORS,
    _round_robin_balanced_indices,
    _validate_manifest_rows,
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
