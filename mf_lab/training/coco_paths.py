from __future__ import annotations

from pathlib import Path

_COCO_PREFIX_TO_SPLIT = {
    "COCO2017_train": "train2017",
    "COCO2017_val": "val2017",
}


def canonical_coco_filename(file_id: str) -> str:
    """Return the canonical COCO 2017 JPEG filename for an AI-GenBench file id.

    AI-GenBench real file lists use compact ids such as
    ``COCO2017_train/468706`` as well as already-canonical names in some
    derived fixtures. COCO 2017 archives/HTTP paths use zero-padded 12-digit
    JPEG filenames, e.g. ``000000468706.jpg``.
    """
    prefix, sep, suffix = str(file_id).partition("/")
    if not sep or prefix not in _COCO_PREFIX_TO_SPLIT:
        raise ValueError(f"unsupported COCO file id: {file_id}")
    raw_name = Path(suffix).name
    stem = Path(raw_name).stem
    if not stem.isdigit():
        raise ValueError(f"COCO file id does not contain a numeric image id: {file_id}")
    return f"{int(stem):012d}.jpg"


def coco_http_url(file_id: str) -> str:
    prefix = str(file_id).split("/", 1)[0]
    try:
        split = _COCO_PREFIX_TO_SPLIT[prefix]
    except KeyError as exc:
        raise ValueError(f"unsupported COCO file id: {file_id}") from exc
    return f"https://images.cocodataset.org/{split}/{canonical_coco_filename(file_id)}"


def coco_zip_member(file_id: str) -> str:
    prefix = str(file_id).split("/", 1)[0]
    try:
        split = _COCO_PREFIX_TO_SPLIT[prefix]
    except KeyError as exc:
        raise ValueError(f"unsupported COCO file id: {file_id}") from exc
    return f"{split}/{canonical_coco_filename(file_id)}"
