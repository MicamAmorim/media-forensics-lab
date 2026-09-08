"""Media Forensics Lab package initialization.

Contains small runtime compatibility guards so forensic modules behave
consistently across Windows/OpenCV builds without changing their analytical
logic.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np


def _unicode_safe_imread(path, flags=cv2.IMREAD_COLOR):
    """Unicode-safe replacement for ``cv2.imread`` on Windows.

    Some OpenCV Windows builds fail when the filesystem path contains
    non-ASCII characters (for example ``Perícia Digital``). Python/NumPy can
    open the path correctly, then OpenCV can decode the bytes via imdecode.
    """
    try:
        data = np.fromfile(Path(path), dtype=np.uint8)
        if data.size:
            image = cv2.imdecode(data, flags)
            if image is not None:
                return image
    except (OSError, ValueError, TypeError):
        pass
    return _ORIGINAL_IMREAD(str(path), flags)


_ORIGINAL_IMREAD = cv2.imread
if os.name == "nt":
    cv2.imread = _unicode_safe_imread


class _UnavailableCascade:
    def __init__(self, *args, **kwargs):
        pass

    def empty(self):
        return True

    def detectMultiScale(self, *args, **kwargs):
        return []


_ORIGINAL_CASCADE_CLASSIFIER = getattr(cv2, "CascadeClassifier", None)


def _unicode_safe_cascade_classifier(filename=None, *args, **kwargs):
    """Load the bundled Haar cascade through an ASCII-safe temporary path.

    On some OpenCV Windows wheels, ``cv2.data.haarcascades`` is produced by
    native code using the active ANSI code page. If the virtual environment is
    inside a directory such as ``Perícia Digital``, the path may be mojibake
    (for example ``Per├¡cia``) and OpenCV's FileStorage cannot open the XML.

    Python itself can still resolve ``cv2.__file__`` with the correct Unicode
    path. For the built-in frontal-face cascade we therefore locate the XML via
    that module path, copy it to the system temporary directory (ASCII-safe on
    typical Windows installations), and let OpenCV load the copy.
    """
    if _ORIGINAL_CASCADE_CLASSIFIER is None:
        return _UnavailableCascade()

    if filename is None:
        return _ORIGINAL_CASCADE_CLASSIFIER(*args, **kwargs)

    requested = Path(str(filename))
    source = requested if requested.is_file() else None

    if source is None and requested.name == "haarcascade_frontalface_default.xml":
        candidate = Path(cv2.__file__).resolve().parent / "data" / requested.name
        if candidate.is_file():
            source = candidate

    if source is None:
        return _ORIGINAL_CASCADE_CLASSIFIER(str(filename), *args, **kwargs)

    load_path = source
    if os.name == "nt" and not str(source).isascii():
        try:
            cache_dir = Path(tempfile.gettempdir()) / "mflab-opencv-data"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cached = cache_dir / source.name
            if not cached.exists() or cached.stat().st_size != source.stat().st_size:
                shutil.copyfile(source, cached)
            load_path = cached
        except OSError:
            load_path = source

    return _ORIGINAL_CASCADE_CLASSIFIER(str(load_path), *args, **kwargs)


if _ORIGINAL_CASCADE_CLASSIFIER is None:
    cv2.CascadeClassifier = _UnavailableCascade
elif os.name == "nt":
    cv2.CascadeClassifier = _unicode_safe_cascade_classifier
