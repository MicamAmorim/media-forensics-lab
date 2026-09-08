from __future__ import annotations
import json
import shutil
from pathlib import Path
from mf_lab.utils.io import run


def _marker_fallback(path: str | Path) -> dict:
    """Non-cryptographic fallback: detect embedded C2PA/JUMBF marker strings."""
    raw = Path(path).read_bytes()
    low = raw.lower()
    marker = b"c2pa" in low and (b"jumb" in low or b"jumd" in low)
    producer = None
    if b"openai media service" in low:
        producer = "OpenAI Media Service"
    elif b"openai" in low:
        producer = "OpenAI"
    return {
        "status": "marker_only" if marker else "unavailable",
        "tool": "builtin_marker_scan",
        "embedded_c2pa_marker_present": bool(marker),
        "producer_hint": producer,
        "cryptographically_validated": False,
        "reason": "c2patool_not_found",
        "note": (
            "Embedded marker detection is not signature validation. Install c2patool to validate the manifest, "
            "certificate chain and assertions."
        ),
    }


def c2pa_inspect(path: str | Path) -> dict:
    """Inspect C2PA Content Credentials; fall back to marker presence when CLI is absent."""
    exe = shutil.which("c2patool")
    if not exe:
        return _marker_fallback(path)
    r = run([exe, str(path), "--json"])
    if r["returncode"] != 0:
        fallback = _marker_fallback(path)
        fallback.update({"status": "tool_error", "tool": "c2patool", "stderr": r["stderr"][-4000:]})
        return fallback
    try:
        data = json.loads(r["stdout"])
    except Exception:
        return {
            "status": "parsed_text",
            "tool": "c2patool",
            "stdout": r["stdout"][-8000:],
            "cryptographically_validated": False,
        }
    text = json.dumps(data, ensure_ascii=False).lower()
    producer = "OpenAI" if "openai" in text else None
    return {
        "status": "success",
        "tool": "c2patool",
        "manifest": data,
        "embedded_c2pa_marker_present": True,
        "producer_hint": producer,
        "cryptographically_validated": True,
    }
