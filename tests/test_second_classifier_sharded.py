from __future__ import annotations

from mf_lab.training.sharded_second_classifier import (
    select_shard_rows,
    shard_index_for_row,
)


def _row(sample_id: str, *, label: int, split: str = "train", row_index: int = 0):
    return {
        "sample_id": sample_id,
        "source_split": split,
        "row_index": str(row_index),
        "label": str(label),
        "role": "fit",
        "generator": "CycleGAN" if label else "(Real)",
        "origin_dataset": "x",
        "file_id": sample_id,
        "sample_rank": "1",
    }


def test_synthetic_rows_on_same_dataset_viewer_page_share_shard():
    a = _row("a", label=1, row_index=101)
    b = _row("b", label=1, row_index=199)
    c = _row("c", label=1, row_index=200)
    assert shard_index_for_row(a, 13) == shard_index_for_row(b, 13)
    # Different page is allowed to hash to the same shard by chance; the key
    # property is same-page co-location, not forced separation.
    assert 0 <= shard_index_for_row(c, 13) < 13


def test_shard_partition_is_complete_disjoint_and_deterministic():
    rows = [
        _row(f"fake-{i}", label=1, row_index=i * 37)
        for i in range(30)
    ] + [
        _row(f"real-{i}", label=0, row_index=-1)
        for i in range(30)
    ]
    first = [select_shard_rows(rows, i, 7) for i in range(7)]
    second = [select_shard_rows(rows, i, 7) for i in range(7)]
    first_ids = [[r["sample_id"] for r in shard] for shard in first]
    second_ids = [[r["sample_id"] for r in shard] for shard in second]
    assert first_ids == second_ids
    flattened = [sample_id for shard in first_ids for sample_id in shard]
    assert len(flattened) == len(rows)
    assert len(flattened) == len(set(flattened))
    assert set(flattened) == {r["sample_id"] for r in rows}
