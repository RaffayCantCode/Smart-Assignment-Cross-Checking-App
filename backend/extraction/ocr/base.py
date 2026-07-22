from typing import Protocol, runtime_checkable

@runtime_checkable
class OCRProvider(Protocol):
    """
    Protocol for any OCR engine.
    """

    @property
    def provider_id(self) -> str:
        """e.g. 'tesseract', 'easyocr'"""
        ...

    def is_available(self) -> bool:
        """Returns True if this provider's runtime dependencies are present."""
        ...

    def extract_text_from_image_bytes(
        self,
        image_bytes: bytes,     # PNG bytes from fitz.Pixmap.tobytes("png")
        dpi: int = 144,
    ) -> str:
        """
        Performs OCR on an in-memory image.
        Returns extracted text, or empty string on failure (never raises).
        Errors are captured as ExtractionWarnings at the caller level.
        """
        ...
