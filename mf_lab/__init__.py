"""Media Forensics Lab package initialization.

Contains small runtime compatibility guards so forensic modules behave
consistently across Windows/OpenCV builds without changing their analytical
logic.
"""
from __future__ import annotations

import os
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


# OpenCV 5 preview/wheel variants may omit the legacy cascade API. The
# deepfake module treats an empty cascade as "face detector unavailable", so
# provide only the minimal compatibility surface needed to degrade gracefully.
if not hasattr(cv2, "CascadeClassifier"):
    class _UnavailableCascade:
        def __init__(self, *args, **kwargs):
            pass

        def empty(self):
            return True

        def detectMultiScale(self, *args, **kwargs):
            return []

    cv2.CascadeClassifier = _UnavailableCascade
