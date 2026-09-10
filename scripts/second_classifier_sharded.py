from __future__ import annotations

import argparse
import glob
import json

from mf_lab.training.sharded_second_classifier import (
    acquire_and_embed_shard,
    merge_embedding_shards,
)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Sharded AI-GenBench-derived Classifier 2 pipeline")
    sub = p.add_subparsers(dest="command", required=True)

    shard = sub.add_parser("embed-shard")
    shard.add_argument("--plan", required=True)
    shard.add_argument("--work-dir", required=True)
    shard.add_argument("--cache-dir", required=True)
    shard.add_argument("--shard-index", type=int, required=True)
    shard.add_argument("--num-shards", type=int, required=True)
    shard.add_argument("--workers", type=int, default=8)
    shard.add_argument("--backbone", default="facebook/dinov2-small")
    shard.add_argument("--batch-size", type=int, default=32)
    shard.add_argument("--device", default="auto")
    shard.add_argument("--keep-raw", action="store_true")

    merge = sub.add_parser("merge")
    merge.add_argument("--plan", required=True)
    merge.add_argument("--shard-glob", required=True)
    merge.add_argument("--out", required=True)

    return p


def main() -> int:
    args = parser().parse_args()
    if args.command == "embed-shard":
        result = acquire_and_embed_shard(
            args.plan,
            args.work_dir,
            cache_dir=args.cache_dir,
            shard_index=args.shard_index,
            num_shards=args.num_shards,
            workers=args.workers,
            backbone=args.backbone,
            batch_size=args.batch_size,
            device=args.device,
            delete_raw_after_embedding=not args.keep_raw,
        )
    elif args.command == "merge":
        paths = sorted(glob.glob(args.shard_glob, recursive=True))
        if not paths:
            raise FileNotFoundError(f"no shard NPZ files matched {args.shard_glob!r}")
        result = merge_embedding_shards(args.plan, paths, args.out)
    else:  # pragma: no cover
        raise AssertionError(args.command)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
