import os
from typing import Optional
from .base import TextExtractor, ProgressCallback
from .pdf_extractor import PDFExtractor
from .docx_extractor import DocxExtractor
from ..domain.document import Document
from ..utils import UnsupportedFileTypeError, FileProcessingError

class DocumentLoader:
    def __init__(self):
        self._extractors: list[TextExtractor] = [
            PDFExtractor(),
            DocxExtractor(),
        ]

    def load(
        self,
        file_path: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Document:
        if not os.path.exists(file_path):
            raise FileProcessingError(f"File not found: {file_path}")

        for extractor in self._extractors:
            if extractor.can_handle(file_path):
                return extractor.extract(file_path, progress_callback)

        ext = os.path.splitext(file_path)[1].lower()
        raise UnsupportedFileTypeError(
            f"No extractor registered for '{ext}'. "
            f"Supported formats: .pdf, .docx"
        )

    def register(self, extractor: TextExtractor) -> None:
        self._extractors.insert(0, extractor)

__all__ = ["DocumentLoader", "TextExtractor"]
