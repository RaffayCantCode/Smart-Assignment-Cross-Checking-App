from typing import Protocol, runtime_checkable, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from PIL import Image

@dataclass(frozen=True)
class OCRResult:
    text: str
    confidence: float

@runtime_checkable
class OCRProvider(Protocol):
    """
    Protocol for any OCR engine.
    """

    @property
    def provider_id(self) -> str:
        """e.g. 'tesseract'"""
        ...

    def is_available(self) -> bool:
        """Returns True if this provider's runtime dependencies are present."""
        ...

    def extract_text_from_image(
        self,
        image: 'Image.Image',
    ) -> OCRResult:
        """
        Performs OCR on an in-memory PIL Image.
        Returns OCRResult(text, confidence), or empty on failure (never raises).
        Errors are captured as ExtractionWarnings at the caller level.
        """
        ...
