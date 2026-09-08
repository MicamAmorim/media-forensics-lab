from __future__ import annotations
import json
from pathlib import Path


def load_case_external_models(case_dir: str | Path, media_name: str) -> list[dict]:
    """Read optional external model evidence from case/external/deepfake_scores.json.

    Schema:
      {"files": {"image.jpg": [{...model result...}]}}
    """
    p = Path(case_dir) / "external" / "deepfake_scores.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("files", {}).get(media_name, []) or []
    except Exception:
        return []
