#!/usr/bin/env python3
"""Clone optional external toolkits on a machine with Internet access.

Nothing is downloaded during normal MFLab installation. This script keeps
third-party code under .external/ and preserves each project's own license.
"""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / ".external"
TOOLS = {
    "veritas": "https://github.com/CodeRafay/Forensic-Image-Analysis-Toolkit.git",
    "deepfakebench": "https://github.com/SCLBD/DeepfakeBench.git",
    "trufor": "https://github.com/grip-unina/TruFor.git",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tools", nargs="*", choices=sorted(TOOLS), default=["veritas"])
    a = ap.parse_args()
    EXT.mkdir(exist_ok=True)
    for name in a.tools:
        url = TOOLS[name]
        dest = EXT / ("Forensic-Image-Analysis-Toolkit" if name == "veritas" else "DeepfakeBench" if name == "deepfakebench" else "TruFor")
        if dest.exists():
            print(f"[skip] {name}: {dest} already exists")
            continue
        print(f"[clone] {name}: {url}")
        subprocess.run(["git", "clone", "--depth", "1", url, str(dest)], check=True)

if __name__ == "__main__":
    main()
