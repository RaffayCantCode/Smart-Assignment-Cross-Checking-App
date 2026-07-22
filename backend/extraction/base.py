from typing import Protocol, runtime_checkable, Callable, Optional
from ..domain.document import Document

ProgressCallback = Callable[[int, str], None]

@runtime_checkable
class TextExtractor(Protocol):
    """
    Protocol for any document format extractor.
    """

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        """e.g. ('.pdf',) or ('.docx', '.doc')"""
        ...

    def extract(
        self,
        file_path: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Document:
        """
        Extracts and returns a complete Document.
        Raises FileProcessingError or UnsupportedFileTypeError on failure.
        Never returns None.
        """
        ...

    def can_handle(self, file_path: str) -> bool:
        """Returns True if this extractor can handle the given file."""
        ...
