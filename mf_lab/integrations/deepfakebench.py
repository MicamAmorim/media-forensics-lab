from __future__ import annotations

import json
import os
from pathlib import Path


def default_path() -> Path:
    env = os.environ.get("DEEPFAKEBENCH_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / ".external" / "DeepfakeBench"


def status(path: str | Path | None = None) -> dict:
    root = Path(path) if path else default_path()
    return {
        "toolkit": "SCLBD/DeepfakeBench",
        "path": str(root),
        "installed": (root / "training").is_dir(),
        "mode": "optional_validated_model_backend",
        "license_note": "Upstream README currently advertises CC BY-NC 4.0; do not vendor or assume commercial redistribution rights without checking each component/weight/dataset license.",
        "note": "DeepfakeBench has its own environment/model weights/dataset requirements; MFLab consumes exported scores rather than pretending its heuristics are equivalent.",
    }


def load_exported_results(result_json: str | Path) -> list[dict]:
    """Load standardized model outputs exported from a DeepfakeBench run.

    Expected JSON can be either a list of model dictionaries or a dict with a
    `models` list. Each model should contain name, score, threshold, decision
    and validation metadata. MFLab will only treat entries explicitly marked
    `validated: true` as validated model evidence.
    """
    p = Path(result_json)
    data = json.loads(p.read_text(encoding="utf-8"))
    models = data.get("models", []) if isinstance(data, dict) else data
    out = []
    for m in models:
        if not isinstance(m, dict):
            continue
        out.append({
            "name": m.get("name", "unknown"),
            "score": m.get("score"),
            "threshold": m.get("threshold"),
            "decision": m.get("decision"),
            "validated": bool(m.get("validated", False)),
            "dataset": m.get("dataset"),
            "checkpoint": m.get("checkpoint"),
            "notes": m.get("notes"),
        })
    return out
