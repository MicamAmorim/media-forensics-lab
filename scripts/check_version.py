from __future__ import annotations

import argparse
import re
import sys
from importlib.metadata import PackageNotFoundError, version as installed_version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', text, re.MULTILINE)
    if not match:
        raise RuntimeError("pyproject.toml does not define a static project version")
    return match.group(1)


def fail(message: str) -> None:
    print(f"VERSION GATE FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate MFLab version metadata")
    parser.add_argument(
        "--tag",
        default=None,
        help="Optional release tag; must be exactly v<pyproject version>",
    )
    args = parser.parse_args()

    value = project_version()
    if not SEMVER.fullmatch(value):
        fail(f"project version '{value}' is not SemVer")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if not re.search(
        rf"^##\s+{re.escape(value)}\s+-\s+\d{{4}}-\d{{2}}-\d{{2}}\s*$",
        changelog,
        re.MULTILINE,
    ):
        fail(f"CHANGELOG.md has no dated section for {value}")

    major, minor, _patch = value.split(".", 2)
    readme_first_line = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()[0]
    if f"v{major}.{minor}" not in readme_first_line:
        fail(
            f"README heading '{readme_first_line}' does not identify release line v{major}.{minor}"
        )

    from mf_lab.version import __version__

    if __version__ != value:
        fail(f"runtime version is {__version__}, pyproject version is {value}")

    try:
        installed = installed_version("media-forensics-lab")
    except PackageNotFoundError:
        installed = None
    if installed is not None and installed != value:
        fail(f"installed distribution is {installed}, pyproject version is {value}")

    if args.tag is not None and args.tag != f"v{value}":
        fail(f"release tag '{args.tag}' must be exactly 'v{value}'")

    print(f"version={value}")
    print("version_gate=pass")


if __name__ == "__main__":
    main()
