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
from mf_lab.training.selective_remote_search import build_selective_plan_search


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
        help="download only selected images and write SHA-256 materialized manifest",
    )
    mat.add_argument("--plan", required=True)
    mat.add_argument("--output-dir", required=True)
    mat.add_argument("--out", required=True)
    mat.add_argument("--max-samples", type=int)

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
        result = build_selective_plan_search(
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
