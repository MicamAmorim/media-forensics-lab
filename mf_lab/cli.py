from __future__ import annotations

import argparse
import json
from pathlib import Path

from mf_lab.integrations.deepfakebench import status as deepfakebench_status
from mf_lab.integrations.veritas import status as veritas_status
from mf_lab.pipeline import PROFILES, analyze_case, analyze_file
from mf_lab.report.generator import generate_preliminary_report


def main():
    ap = argparse.ArgumentParser(prog="mflab")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("analyze-file")
    p.add_argument("file")
    p.add_argument("--out", default="results")
    p.add_argument("--profile", choices=sorted(PROFILES), default="full")
    p.add_argument("--veritas", action="store_true", help="Run optional CodeRafay/Veritas checkout as secondary cross-check")

    p = sp.add_parser("analyze-case")
    p.add_argument("case_dir")
    p.add_argument("--profile", choices=sorted(PROFILES), default="full")
    p.add_argument("--veritas", action="store_true", help="Run optional CodeRafay/Veritas checkout as secondary cross-check")

    p = sp.add_parser("report")
    p.add_argument("case_dir")
    p.add_argument("--format", choices=["docx", "md"], default="docx")

    sp.add_parser("integrations", help="Show optional upstream integration status")

    a = ap.parse_args()
    if a.cmd == "analyze-file":
        analyze_file(a.file, a.out, profile=a.profile, run_veritas=a.veritas)
    elif a.cmd == "analyze-case":
        analyze_case(a.case_dir, profile=a.profile, run_veritas=a.veritas)
    elif a.cmd == "report":
        print(generate_preliminary_report(a.case_dir, a.format))
    elif a.cmd == "integrations":
        print(json.dumps({"veritas": veritas_status(), "deepfakebench": deepfakebench_status()}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
