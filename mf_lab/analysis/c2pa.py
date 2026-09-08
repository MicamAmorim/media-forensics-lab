from __future__ import annotations
import json
import shutil
from pathlib import Path
from mf_lab.utils.io import run


def c2pa_inspect(path: str | Path) -> dict:
    """Inspect C2PA Content Credentials when c2patool is installed."""
    exe = shutil.which("c2patool")
    if not exe:
        return {
            "status": "unavailable",
            "tool": "c2patool",
            "reason": "c2patool_not_found",
            "note": "Install the official C2PA CLI to enable cryptographic provenance validation.",
        }
    # `c2patool <asset> --json` is supported by the official CLI releases.
    r = run([exe, str(path), "--json"])
    if r["returncode"] != 0:
        return {"status": "error", "tool": "c2patool", "stderr": r["stderr"][-4000:]}
    try:
        data = json.loads(r["stdout"])
    except Exception:
        return {"status": "parsed_text", "tool": "c2patool", "stdout": r["stdout"][-8000:]}
    return {"status": "success", "tool": "c2patool", "manifest": data}
