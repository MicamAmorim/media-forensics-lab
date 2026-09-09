from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .selective_acquisition import extract_materialized_embeddings


def validate_materialized_manifest(path: str | Path) -> dict:
    """Refuse silent sample shrinkage before scientific training.

    Every planned row must have a local file and a SHA-256. The class balance of
    every role is rechecked after acquisition so dead URLs cannot silently alter
    the training/evaluation distribution. The stored digest is recomputed from
    the materialized bytes so a stale or corrupted cache cannot pass the gate.
    """
    import hashlib

    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("materialized manifest is empty")

    missing: list[str] = []
    bad_hash: list[str] = []
    hash_mismatch: list[str] = []
    role_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"real": 0, "synthetic": 0}
    )
    for row in rows:
        label = int(row["label"])
        role_counts[str(row["role"])]["synthetic" if label else "real"] += 1
        sample_id = str(row.get("sample_id") or "(unknown)")
        local_path = str(row.get("local_path") or "")
        sha256 = str(row.get("sha256") or "")
        path_obj = Path(local_path) if local_path else None
        if path_obj is None or not path_obj.is_file():
            missing.append(sample_id)
            continue
        if len(sha256) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in sha256):
            bad_hash.append(sample_id)
            continue
        actual = hashlib.sha256(path_obj.read_bytes()).hexdigest()
        if actual.lower() != sha256.lower():
            hash_mismatch.append(sample_id)

    unbalanced = {
        role: counts
        for role, counts in role_counts.items()
        if counts["real"] != counts["synthetic"]
    }
    if missing or bad_hash or hash_mismatch or unbalanced:
        problems = []
        if missing:
            problems.append(f"missing_local_files={len(missing)}")
        if bad_hash:
            problems.append(f"missing_or_invalid_sha256={len(bad_hash)}")
        if hash_mismatch:
            problems.append(f"sha256_mismatch={len(hash_mismatch)}")
        if unbalanced:
            problems.append(f"unbalanced_roles={unbalanced}")
        raise ValueError(
            "selective sample is not training-ready: " + "; ".join(problems)
        )

    return {
        "rows": len(rows),
        "roles": dict(role_counts),
        "complete": True,
        "all_sha256_present": True,
        "all_sha256_verified": True,
    }


def extract_verified_materialized_embeddings(
    manifest_csv: str | Path,
    out_npz: str | Path,
    **kwargs,
) -> dict:
    validation = validate_materialized_manifest(manifest_csv)
    result = extract_materialized_embeddings(manifest_csv, out_npz, **kwargs)
    return {**result, "materialized_manifest_validation": validation}
