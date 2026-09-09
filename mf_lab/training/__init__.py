"""Training utilities for experimental MFLab classifiers.

Modules in this package keep heavy ML dependencies optional and import them lazily.
"""

from .second_classifier import (
    AI_GENBENCH_GENERATORS,
    DEFAULT_OOD_GENERATORS,
    build_manifest,
    extract_embeddings,
    train_head,
)

__all__ = [
    "AI_GENBENCH_GENERATORS",
    "DEFAULT_OOD_GENERATORS",
    "build_manifest",
    "extract_embeddings",
    "train_head",
]
