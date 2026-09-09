from __future__ import annotations

import argparse
import json

from mf_lab.training.selective_acquisition import (
    DEFAULT_BACKBONE,
    DEFAULT_OOD_GENERATORS,
    DEFAULT_SEED,
    materialize_plan,
)
from mf_lab.training.selective_embeddings import (
    extract_verified_materialized_embeddings,
)
from mf_lab.training.selective_remote_rows import build_selective_plan_rows
from mf_lab.training.stable_real_acquisition import (
    freeze_materialized_corpus,
    materialize_stable_plan,
)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Selective AI-GenBench acquisition for the MFLab second classifier"
    )
    sub = p.add_subparsers(dest="command", required=True)

    plan = sub.add_parser(
        "build-plan",
        help="build a deterministic remote acquisition plan without downloading full shards",
    )
    plan.add_argument("--out", required=True)
    plan.add_argument("--cache-dir", required=True)
    plan.add_argument("--fit-per-generator", type=int, default=500)
    plan.add_argument("--calibration-per-generator", type=int, default=125)
    plan.add_argument("--iid-test-per-generator", type=int, default=125)
    plan.add_argument("--ood-per-generator", type=int, default=500)
    plan.add_argument("--ood-generators", nargs="*", default=list(DEFAULT_OOD_GENERATORS))
    plan.add_argument("--seed", type=int, default=DEFAULT_SEED)

    mat = sub.add_parser(
        "materialize",
        help="legacy direct downloader retained for diagnostics/small experiments",
    )
    mat.add_argument("--plan", required=True)
    mat.add_argument("--output-dir", required=True)
    mat.add_argument("--out", required=True)
    mat.add_argument("--max-samples", type=int)

    stable = sub.add_parser(
        "materialize-stable",
        help="stable acquisition: synthetic direct, COCO official ZIP, LAION audited replacements",
    )
    stable.add_argument("--plan", required=True)
    stable.add_argument("--output-dir", required=True)
    stable.add_argument("--out", required=True)
    stable.add_argument("--cache-dir", required=True)
    stable.add_argument("--archive-cache")
    stable.add_argument("--diagnostics-out")
    stable.add_argument("--replacement-log-out")
    stable.add_argument("--max-samples", type=int)
    stable.add_argument("--seed", type=int, default=DEFAULT_SEED)
    stable.add_argument("--max-laion-replacements-per-sample", type=int, default=8)

    freeze = sub.add_parser(
        "freeze-corpus",
        help="verify every byte/hash and emit a frozen scientific corpus manifest + lock",
    )
    freeze.add_argument("--manifest", required=True)
    freeze.add_argument("--frozen-manifest", required=True)
    freeze.add_argument("--lock", required=True)
    freeze.add_argument("--replacement-log")

    emb = sub.add_parser(
        "extract-embeddings",
        help="verify the complete sample and extract frozen DINOv2 embeddings",
    )
    emb.add_argument("--manifest", required=True)
    emb.add_argument("--out", required=True)
    emb.add_argument("--backbone", default=DEFAULT_BACKBONE)
    emb.add_argument("--batch-size", type=int, default=32)
    emb.add_argument("--device", default="auto")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.command == "build-plan":
        result = build_selective_plan_rows(
            args.out,
            cache_dir=args.cache_dir,
            fit_per_generator=args.fit_per_generator,
            calibration_per_generator=args.calibration_per_generator,
            iid_test_per_generator=args.iid_test_per_generator,
            ood_per_generator=args.ood_per_generator,
            ood_generators=args.ood_generators,
            seed=args.seed,
        )
    elif args.command == "materialize":
        result = materialize_plan(
            args.plan,
            args.output_dir,
            args.out,
            max_samples=args.max_samples,
        )
    elif args.command == "materialize-stable":
        result = materialize_stable_plan(
            args.plan,
            args.output_dir,
            args.out,
            cache_dir=args.cache_dir,
            archive_cache=args.archive_cache,
            diagnostics_out=args.diagnostics_out,
            replacement_log_out=args.replacement_log_out,
            max_samples=args.max_samples,
            seed=args.seed,
            max_laion_replacements_per_sample=args.max_laion_replacements_per_sample,
        )
    elif args.command == "freeze-corpus":
        result = freeze_materialized_corpus(
            args.manifest,
            args.frozen_manifest,
            args.lock,
            replacement_log=args.replacement_log,
        )
    elif args.command == "extract-embeddings":
        result = extract_verified_materialized_embeddings(
            args.manifest,
            args.out,
            backbone=args.backbone,
            batch_size=args.batch_size,
            device=args.device,
        )
    else:  # pragma: no cover
        raise AssertionError(args.command)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
