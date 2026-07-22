from enum import Enum
from dataclasses import dataclass

class ExtractionMethod(str, Enum):
    DIGITAL_TEXT = "digital_text"
    OCR          = "ocr"
    OCR_HYBRID   = "ocr_hybrid"
    DOCX         = "docx"

@dataclass(frozen=True)
class Sentence:
    text: str
    index: int
    char_start: int
    char_end: int

@dataclass(frozen=True)
class Paragraph:
    text: str
    index: int
    page_number: int
    word_count: int
    char_count: int
    is_ocr_derived: bool
    sentences: tuple['Sentence', ...]

    @property
    def sentence_count(self) -> int:
        return len(self.sentences)

@dataclass(frozen=True)
class ExtractionWarning:
    code: str
    message: str
    page: int

@dataclass(frozen=True)
class ExtractionInfo:
    method: ExtractionMethod
    page_count: int
    ocr_page_count: int
    extraction_time_s: float
    warnings: tuple[ExtractionWarning, ...]

@dataclass(frozen=True)
class DocumentSource:
    file_path: str
    file_name: str
    extension: str
    file_size_bytes: int
    mtime: float

@dataclass(frozen=True)
class DocumentContent:
    raw_text: str
    paragraphs: tuple[Paragraph, ...]
    word_count: int
    paragraph_count: int
    sentence_count: int

@dataclass(frozen=True)
class Document:
    source: DocumentSource
    content: DocumentContent
    extraction_info: ExtractionInfo

    @property
    def file_name(self) -> str:
        return self.source.file_name

    @property
    def paragraphs(self) -> tuple[Paragraph, ...]:
        return self.content.paragraphs

    @property
    def paragraph_texts(self) -> list[str]:
        return [p.text for p in self.content.paragraphs]

    @property
    def all_sentences(self) -> list[Sentence]:
        return [s for p in self.content.paragraphs for s in p.sentences]

    @property
    def is_empty(self) -> bool:
        return self.content.paragraph_count == 0

    @property
    def has_ocr_content(self) -> bool:
        return self.extraction_info.method in (
            ExtractionMethod.OCR, ExtractionMethod.OCR_HYBRID
        )
