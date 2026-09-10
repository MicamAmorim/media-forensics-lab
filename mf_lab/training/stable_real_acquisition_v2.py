from __future__ import annotations

from pathlib import Path
from typing import Mapping

from . import stable_real_acquisition as _legacy
from .coco_paths import coco_zip_member

# Re-export the immutable freeze implementation.
freeze_materialized_corpus = _legacy.freeze_materialized_corpus


def materialize_stable_plan(
    plan_csv: str | Path,
    output_dir: str | Path,
    out_csv: str | Path,
    *,
    cache_dir: str | Path,
    archive_cache: str | Path | None = None,
    diagnostics_out: str | Path | None = None,
    replacement_log_out: str | Path | None = None,
    max_samples: int | None = None,
    seed: int = _legacy.DEFAULT_SEED,
    max_laion_replacements_per_sample: int = 8,
    archive_paths: Mapping[str, str | Path] | None = None,
) -> dict:
    """Canonical COCO wrapper around the stable acquisition implementation.

    The original implementation pre-dated discovery that official AI-GenBench
    COCO ids are compact numeric ids. This wrapper preserves the tested stable
    LAION/freeze path but canonicalizes COCO ZIP member names and uses the COCO
    published HTTP archive transport rather than disabling TLS verification.

    The patching is scoped to this synchronous call and restored in ``finally``;
    the scientific CLI invokes acquisition in one process, not concurrently.
    """
    original_member = _legacy._coco_member_name
    original_urls = {
        prefix: str(spec["url"])
        for prefix, spec in _legacy.COCO_ARCHIVES.items()
    }

    def _canonical_member(file_id: str, prefix: str) -> str:
        observed_prefix = str(file_id).split("/", 1)[0]
        if observed_prefix != prefix:
            raise ValueError(
                f"COCO prefix mismatch: expected={prefix} observed={observed_prefix}"
            )
        return coco_zip_member(file_id)

    try:
        _legacy._coco_member_name = _canonical_member
        _legacy.COCO_ARCHIVES["COCO2017_train"]["url"] = (
            "http://images.cocodataset.org/zips/train2017.zip"
        )
        _legacy.COCO_ARCHIVES["COCO2017_val"]["url"] = (
            "http://images.cocodataset.org/zips/val2017.zip"
        )
        result = _legacy.materialize_stable_plan(
            plan_csv,
            output_dir,
            out_csv,
            cache_dir=cache_dir,
            archive_cache=archive_cache,
            diagnostics_out=diagnostics_out,
            replacement_log_out=replacement_log_out,
            max_samples=max_samples,
            seed=seed,
            max_laion_replacements_per_sample=max_laion_replacements_per_sample,
            archive_paths=archive_paths,
        )
        result = dict(result)
        result["coco_id_policy"] = "canonical_zero_padded_12_digit_jpeg"
        result["coco_archive_transport"] = "official_http_endpoint"
        return result
    finally:
        _legacy._coco_member_name = original_member
        for prefix, url in original_urls.items():
            _legacy.COCO_ARCHIVES[prefix]["url"] = url
