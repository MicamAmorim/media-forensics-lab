from __future__ import annotations

import json
import shutil
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from mf_lab.utils.io import run


def _producer_hint(data: dict) -> str | None:
    text = json.dumps(data, ensure_ascii=False).lower()
    if "openai media service" in text:
        return "OpenAI Media Service"
    if "openai" in text:
        return "OpenAI"
    return None


def _validation_summary(data: dict, tool: str) -> dict:
    """Conservatively summarize C2PA integrity validation without equating it to trust."""
    active_label = data.get("active_manifest")
    manifests = data.get("manifests") if isinstance(data.get("manifests"), dict) else {}
    active_manifest = manifests.get(active_label, {}) if active_label else {}
    validation_state = active_manifest.get("validation_state") or data.get("validation_state")

    results = data.get("validation_results") if isinstance(data.get("validation_results"), dict) else {}
    active_results = results.get("activeManifest") or results.get("active_manifest") or {}
    successes = active_results.get("success") if isinstance(active_results, dict) else []
    failures = active_results.get("failure") if isinstance(active_results, dict) else []
    successes = successes if isinstance(successes, list) else []
    failures = failures if isinstance(failures, list) else []

    success_codes = {str(row.get("code")) for row in successes if isinstance(row, dict)}
    failure_codes = [str(row.get("code")) for row in failures if isinstance(row, dict)]
    signature_validated = "claimSignature.validated" in success_codes
    data_hash_validated = "assertion.dataHash.match" in success_codes

    cryptographically_validated = bool(active_label and signature_validated and not failure_codes)
    if str(validation_state).lower() == "invalid":
        cryptographically_validated = False

    if cryptographically_validated:
        status = "validated"
    elif failure_codes or str(validation_state).lower() == "invalid":
        status = "invalid"
    elif active_label:
        status = "manifest_present_unverified"
    else:
        status = "no_active_manifest"

    return {
        "status": status,
        "tool": tool,
        "manifest_present": bool(active_label),
        "embedded_c2pa_marker_present": bool(active_label),
        "active_manifest": active_label,
        "producer_hint": _producer_hint(data),
        "validation_state": validation_state,
        "signature_validated": signature_validated,
        "data_hash_validated": data_hash_validated,
        "validation_failure_count": len(failure_codes),
        "validation_failures": failure_codes[:25],
        "cryptographically_validated": cryptographically_validated,
        "manifest": data,
        "note": (
            "C2PA cryptographic integrity validation is provenance evidence, not proof that the depicted content is true. "
            "Certificate trust is a separate question and depends on configured trust anchors."
        ),
    }


def _marker_fallback(path: str | Path, reason: str = "c2pa_validator_not_available") -> dict:
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
        "manifest_present": bool(marker),
        "producer_hint": producer,
        "cryptographically_validated": False,
        "reason": reason,
        "note": (
            "Embedded marker detection is not signature validation. Install c2pa-python or c2patool to validate the manifest, "
            "asset binding and signature."
        ),
    }


def _inspect_with_python_sdk(path: str | Path) -> dict:
    import c2pa

    with c2pa.Context() as context:
        with c2pa.Reader(str(path), context=context) as reader:
            payload = reader.detailed_json()
    data = json.loads(payload)
    out = _validation_summary(data, "c2pa-python")
    try:
        out["tool_version"] = version("c2pa-python")
    except PackageNotFoundError:
        pass
    return out


def _inspect_with_cli(path: str | Path, exe: str) -> dict:
    r = run([exe, str(path), "--json"])
    if r["returncode"] != 0:
        raise RuntimeError(r["stderr"][-4000:] or f"c2patool exited with {r['returncode']}")
    data = json.loads(r["stdout"])
    return _validation_summary(data, "c2patool")


def c2pa_inspect(path: str | Path) -> dict:
    """Read and validate C2PA Content Credentials, with a marker-only last-resort fallback."""
    sdk_error = None
    try:
        return _inspect_with_python_sdk(path)
    except ImportError:
        sdk_error = "c2pa_python_not_installed"
    except Exception as exc:
        sdk_error = f"c2pa_python_error:{type(exc).__name__}:{str(exc)[:500]}"

    exe = shutil.which("c2patool")
    if exe:
        try:
            return _inspect_with_cli(path, exe)
        except Exception as exc:
            return _marker_fallback(path, reason=f"c2patool_error:{type(exc).__name__}:{str(exc)[:500]}")

    return _marker_fallback(path, reason=sdk_error or "c2pa_validator_not_available")
