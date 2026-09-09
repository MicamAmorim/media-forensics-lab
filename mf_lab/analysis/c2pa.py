from __future__ import annotations

import json
import shutil
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from mf_lab.utils.io import run


def _producer_hint(data: dict) -> str | None:
    text = json.dumps(data, ensure_ascii=False).lower()
    if "openai media service" in text:
        return "OpenAI Media Service"
    if "openai" in text:
        return "OpenAI"
    return None


def _state_text(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        value = getattr(value, "value")
    text = str(value).strip()
    if "." in text and text.lower().startswith("validationstate"):
        text = text.rsplit(".", 1)[-1]
    return text or None


def _validation_rows(results: Any) -> list[dict]:
    """Flatten SDK validation results while preserving success/failure scope."""
    rows: list[dict] = []

    def walk(node: Any, scope: str = "root", inherited_kind: str | None = None) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item, scope=scope, inherited_kind=inherited_kind)
            return
        if not isinstance(node, dict):
            return

        if "code" in node:
            success = node.get("success")
            kind = inherited_kind
            if kind is None and isinstance(success, bool):
                kind = "success" if success else "failure"
            row = {
                "scope": scope,
                "kind": kind or "status",
                "code": str(node.get("code")),
            }
            for key in ("explanation", "url"):
                if node.get(key) is not None:
                    row[key] = str(node.get(key))
            if isinstance(success, bool):
                row["success"] = success
            rows.append(row)
            return

        for key, value in node.items():
            low = str(key).lower()
            kind = inherited_kind
            if low in {"success", "successes"}:
                kind = "success"
            elif low in {"failure", "failures", "error", "errors"}:
                kind = "failure"
            elif low in {"informational", "info", "warning", "warnings"}:
                kind = "informational"
            child_scope = str(key) if scope == "root" else f"{scope}.{key}"
            walk(value, scope=child_scope, inherited_kind=kind)

    walk(results)
    return rows


def _active_manifest_data(data: dict, active_label: str | None, explicit_active: Any = None) -> dict:
    if isinstance(explicit_active, dict):
        return explicit_active
    manifests = data.get("manifests") if isinstance(data.get("manifests"), dict) else {}
    active = manifests.get(active_label, {}) if active_label else {}
    return active if isinstance(active, dict) else {}


def _validation_summary(
    data: dict,
    tool: str,
    *,
    validation_state: Any = None,
    validation_results: Any = None,
    active_manifest_data: Any = None,
    embedded: bool | None = None,
    remote_url: str | None = None,
) -> dict:
    """Summarize C2PA integrity, trust and diagnostics without equating provenance to truth."""
    active_label = data.get("active_manifest")
    active_manifest = _active_manifest_data(data, active_label, active_manifest_data)

    state = _state_text(
        validation_state
        if validation_state is not None
        else active_manifest.get("validation_state") or data.get("validation_state")
    )
    results = validation_results if validation_results is not None else data.get("validation_results")
    rows = _validation_rows(results if results is not None else {})

    success_rows = [r for r in rows if r.get("kind") == "success" or r.get("success") is True]
    failure_rows = [r for r in rows if r.get("kind") == "failure" or r.get("success") is False]
    informational_rows = [r for r in rows if r.get("kind") == "informational"]
    success_codes = {str(row.get("code")) for row in success_rows}
    failure_codes = [str(row.get("code")) for row in failure_rows]

    signature_validated = "claimSignature.validated" in success_codes
    data_hash_validated = "assertion.dataHash.match" in success_codes

    state_lower = (state or "").lower()
    state_integrity_valid = state_lower in {"valid", "trusted"}
    integrity_validated = bool(
        active_label
        and not failure_codes
        and (state_integrity_valid or signature_validated)
    )
    if state_lower == "invalid":
        integrity_validated = False

    signature_trusted = state_lower == "trusted"
    if signature_trusted:
        trust_status = "trusted"
    elif state_lower == "valid":
        trust_status = "valid_but_not_trusted"
    elif state_lower == "invalid":
        trust_status = "invalid"
    elif active_label:
        trust_status = "not_established"
    else:
        trust_status = "not_applicable"

    if integrity_validated:
        status = "validated"
    elif failure_codes or state_lower == "invalid":
        status = "invalid"
    elif active_label:
        status = "manifest_present_unverified"
    else:
        status = "no_active_manifest"

    signature_info = active_manifest.get("signature_info")
    signature_info = signature_info if isinstance(signature_info, dict) else {}
    claim_generator_info = active_manifest.get("claim_generator_info")
    if not isinstance(claim_generator_info, list):
        claim_generator_info = []
    assertions = active_manifest.get("assertions")
    assertion_labels = []
    if isinstance(assertions, list):
        assertion_labels = [
            str(x.get("label"))
            for x in assertions
            if isinstance(x, dict) and x.get("label")
        ]

    producer = _producer_hint(active_manifest or data)
    manifest_present = bool(active_label)
    if embedded is None:
        embedded_value = None
        manifest_location = "unknown" if manifest_present else "none"
    else:
        embedded_value = bool(embedded)
        manifest_location = "embedded" if embedded_value else ("remote_or_external" if manifest_present else "none")

    return {
        "status": status,
        "tool": tool,
        "manifest_present": manifest_present,
        "embedded_c2pa_marker_present": manifest_present,
        "active_manifest": active_label,
        "manifest_location": manifest_location,
        "is_embedded": embedded_value,
        "remote_url": remote_url,
        "producer_hint": producer,
        "claim_generator": active_manifest.get("claim_generator"),
        "claim_generator_info": claim_generator_info,
        "title": active_manifest.get("title"),
        "assertion_labels": assertion_labels,
        "signature_info": signature_info,
        "validation_state": state,
        "trust_status": trust_status,
        "signature_trusted": signature_trusted,
        "integrity_validated": integrity_validated,
        "signature_validated": signature_validated,
        "data_hash_validated": data_hash_validated,
        "validation_success_count": len(success_rows),
        "validation_failure_count": len(failure_rows),
        "validation_informational_count": len(informational_rows),
        "validation_successes": [str(row.get("code")) for row in success_rows[:50]],
        "validation_failures": failure_codes[:50],
        "validation_statuses": rows[:100],
        "cryptographically_validated": integrity_validated,
        "manifest": data,
        "note": (
            "C2PA validation distinguishes asset/manifest integrity from signer trust. "
            "ValidationState=Valid means no validation errors but the active signature is not trusted; "
            "ValidationState=Trusted means the manifest is valid and the active signature is trusted. "
            "Neither state proves that the depicted content is factually true."
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
        "manifest_location": "unknown" if marker else "none",
        "producer_hint": producer,
        "validation_state": None,
        "trust_status": "not_evaluated",
        "signature_trusted": False,
        "integrity_validated": False,
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
            store = json.loads(reader.json())

            try:
                state = reader.get_validation_state()
            except Exception:
                state = None
            try:
                results = reader.get_validation_results()
            except Exception:
                results = None
            try:
                active = reader.get_active_manifest()
            except Exception:
                active = None
            try:
                embedded = reader.is_embedded()
            except Exception:
                embedded = None
            try:
                remote_url = reader.get_remote_url()
            except Exception:
                remote_url = None

            out = _validation_summary(
                store,
                "c2pa-python",
                validation_state=state,
                validation_results=results,
                active_manifest_data=active,
                embedded=embedded,
                remote_url=remote_url,
            )

            # Keep the richer SDK representation available for case review without
            # using it as the primary source for validation-state semantics.
            try:
                out["detailed_manifest"] = json.loads(reader.detailed_json())
            except Exception as exc:
                out["detailed_manifest_error"] = f"{type(exc).__name__}:{str(exc)[:500]}"

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
