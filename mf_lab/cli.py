from __future__ import annotations

import argparse
import json

from mf_lab.integrations.deepfakebench import status as deepfakebench_status
from mf_lab.integrations.veritas import status as veritas_status
from mf_lab.pipeline import PROFILES, analyze_case, analyze_file
from mf_lab.report.generator import generate_preliminary_report
from mf_lab.validation import validate_demo


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

    p = sp.add_parser("validate-demo", help="Run controlled regression validation against dataset/demo ground truth")
    p.add_argument("--dataset", default=None, help="Optional demo dataset directory")
    p.add_argument("--out", default="validation/demo_validation.json")

    p = sp.add_parser("web", help="Launch the local interactive HTML forensic report")
    p.add_argument("--host", default="127.0.0.1", help="Bind address; keep 127.0.0.1 for local-only use")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--debug", action="store_true")

    a = ap.parse_args()
    if a.cmd == "analyze-file":
        analyze_file(a.file, a.out, profile=a.profile, run_veritas=a.veritas)
    elif a.cmd == "analyze-case":
        analyze_case(a.case_dir, profile=a.profile, run_veritas=a.veritas)
    elif a.cmd == "report":
        print(generate_preliminary_report(a.case_dir, a.format))
    elif a.cmd == "integrations":
        print(json.dumps({"veritas": veritas_status(), "deepfakebench": deepfakebench_status()}, indent=2, ensure_ascii=False))
    elif a.cmd == "validate-demo":
        result = validate_demo(a.dataset, a.out)
        print(json.dumps(result["summary"], indent=2, ensure_ascii=False))
        print(f"validation_report={a.out}")
    elif a.cmd == "web":
        from mf_lab.webapp import run_web
        run_web(host=a.host, port=a.port, debug=a.debug)


if __name__ == "__main__":
    main()
