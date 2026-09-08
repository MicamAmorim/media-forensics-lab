from __future__ import annotations
import json, shutil
from pathlib import Path
from PIL import Image, ExifTags
from mf_lab.utils.io import run


def image_metadata(path: str | Path) -> dict:
    path = Path(path)
    out = {"file": str(path), "kind": "image"}
    try:
        with Image.open(path) as im:
            out.update({"format": im.format, "mode": im.mode, "size": list(im.size)})
            ex = im.getexif()
            out["exif"] = {ExifTags.TAGS.get(k, str(k)): str(v) for k, v in ex.items()}
    except Exception as e:
        out["error"] = repr(e)
    if shutil.which("exiftool"):
        r = run(["exiftool", "-j", "-a", "-u", "-g1", str(path)])
        if r["returncode"] == 0:
            try: out["exiftool"] = json.loads(r["stdout"])[0]
            except Exception: pass
    return out


def video_metadata(path: str | Path) -> dict:
    path = Path(path)
    r = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-print_format", "json", str(path)])
    if r["returncode"] != 0:
        return {"file": str(path), "kind": "video", "error": r["stderr"]}
    data = json.loads(r["stdout"])
    return {"file": str(path), "kind": "video", **data}
