"""
backend/file_loader.py

DEPRECATED: Use backend.extraction.DocumentLoader instead.
This file is kept for backward compatibility for one release.
"""

import warnings
from .extraction import DocumentLoader

def extract_text_from_file(file_path: str) -> str:
    warnings.warn(
        "extract_text_from_file is deprecated. Use DocumentLoader.load() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    loader = DocumentLoader()
    doc = loader.load(file_path)
    return doc.content.raw_text
