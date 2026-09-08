from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_PACKAGE_NAME = "media-forensics-lab"
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def _version_from_pyproject() -> str | None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    if not pyproject.is_file():
        return None
    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', text, re.MULTILINE)
    return match.group(1) if match else None


def current_version() -> str:
    """Return the installed package version, with a source-tree fallback."""
    try:
        value = version(_PACKAGE_NAME)
    except PackageNotFoundError:
        value = _version_from_pyproject() or "0.0.0+unknown"
    return value


__version__ = current_version()


def is_semver(value: str) -> bool:
    return bool(_SEMVER_RE.fullmatch(value))
