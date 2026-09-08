from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from mf_lab.validation import validate_demo

ROOT = Path(__file__).resolve().parents[1]


def _write_job_summary(summary: dict, output_path: Path) -> None:
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if not target:
        return
    rows = [
        "## MFLab ground-truth gate",
        "",
        "| Metric | Result | Required |",
        "|---|---:|---:|",
        f"| GT fixture coverage | {summary['gt_fixture_coverage_pct']:.1f}% | 100% |",
        f"| GT fixture pass rate | {summary['gt_fixture_pass_rate_pct']:.1f}% | 100% |",
        f"| GT assertion coverage | {summary['gt_assertion_coverage_pct']:.1f}% | 100% |",
        f"| GT assertion pass rate | {summary['gt_pass_rate_pct']:.1f}% | 100% |",
        f"| Contract errors | {summary['gt_contract_errors']} | 0 |",
        f"| Unsupported required checks | {summary['unsupported']} | 0 |",
        "",
        f"Validation report: `{output_path.as_posix()}`",
        "",
        "> 100% here means 100% regression coverage/pass against the controlled GT contract. It is not a population-level forensic accuracy estimate.",
        "",
    ]
    with open(target, "a", encoding="utf-8") as fh:
        fh.write("\n".join(rows))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fail CI unless the canonical demo GT is fully covered and passes"
    )
    parser.add_argument("--dataset", default=str(ROOT / "dataset" / "demo"))
    parser.add_argument("--out", default=str(ROOT / "validation" / "demo_validation.json"))
    args = parser.parse_args()

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = validate_demo(args.dataset, output)
    summary = result["summary"]

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    _write_job_summary(summary, output)

    required_100 = (
        summary.get("gt_fixture_coverage_pct") == 100.0
        and summary.get("gt_fixture_pass_rate_pct") == 100.0
        and summary.get("gt_assertion_coverage_pct") == 100.0
        and summary.get("gt_pass_rate_pct") == 100.0
        and summary.get("gt_contract_errors") == 0
        and summary.get("unsupported") == 0
        and summary.get("failed") == 0
        and summary.get("ready_for_demo_regression") is True
    )
    if not required_100:
        print(
            "GT GATE FAILED: CI requires 100% fixture/assertion coverage and pass rate, "
            "zero contract errors, zero unsupported required checks and zero failures.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print("gt_gate=pass")


if __name__ == "__main__":
    main()
