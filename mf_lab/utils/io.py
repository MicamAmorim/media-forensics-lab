from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def sha256(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: str | Path, obj: Any) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: str | Path, default=None):
    p = Path(path)
    if not p.exists(): return default
    return json.loads(p.read_text(encoding="utf-8"))


def run(cmd: list[str], check: bool = False) -> dict[str, Any]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError(p.stderr.strip() or "command failed")
    return {"cmd": cmd, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def cv_imread(path: str | Path, flags: int = cv2.IMREAD_COLOR):
    """Unicode-safe OpenCV image read, especially for Windows evidence paths."""
    p = Path(path)
    try:
        data = np.fromfile(p, dtype=np.uint8)
        img = cv2.imdecode(data, flags)
    except Exception:
        img = None
    if img is None:
        img = cv2.imread(str(p), flags)
    return img
