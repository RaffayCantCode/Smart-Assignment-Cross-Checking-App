from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MatchType(str, Enum):
    EXACT = "exact"
    PARTIAL = "partial"
    SEMANTIC = "semantic"
    UNIQUE = "unique"
    NONE = "none"

    @classmethod
    def from_score(cls, score: float) -> 'MatchType':
        if score >= 0.95:
            return cls.EXACT
        elif score >= 0.70:
            return cls.PARTIAL
        elif score >= 0.40:
            return cls.SEMANTIC
        return cls.UNIQUE


@dataclass(frozen=True)
class ReportSpan:
    char_start: int
    char_end: int
    match_type: MatchType
    match_id: int


def _make_paragraph_id(side: str, index: int) -> str:
    return f"{side}-{index + 1:04d}"


@dataclass(frozen=True)
class ReportParagraph:
    index: int
    paragraph_id: str
    text: str
    spans: tuple[ReportSpan, ...]
    primary_match_type: MatchType
    is_matched: bool
    match_score: float = 0.0
    matched_paragraph_index: Optional[int] = None
    matched_paragraph_id: str = ""
    sentence_count: int = 0
    word_count: int = 0
    is_ocr_derived: bool = False


@dataclass(frozen=True)
class ReportDocument:
    title: str
    paragraphs: tuple[ReportParagraph, ...]


@dataclass(frozen=True)
class ReportMatch:
    match_id: int
    type: MatchType
    left_paragraph_index: int
    right_paragraph_index: int
    left_paragraph_id: str
    right_paragraph_id: str
    score: float
    left_sentence_indices: tuple[int, ...] = ()
    right_sentence_indices: tuple[int, ...] = ()


@dataclass(frozen=True)
class ReportStatistics:
    similarity_percent: int
    total_matches: int
    exact_matches: int
    partial_matches: int
    semantic_matches: int
    unique_paragraphs: int
    ocr_used: bool
    avg_ocr_confidence: float = 0.0
    confidence: float = 0.0


@dataclass(frozen=True)
class SearchResult:
    paragraph_index: int
    paragraph_id: str
    char_start: int
    char_end: int
    document_side: str


@dataclass(frozen=True)
class ReportModel:
    statistics: ReportStatistics
    left_document: ReportDocument
    right_document: ReportDocument
    matches: tuple[ReportMatch, ...]

    def search(self, query: str) -> tuple[SearchResult, ...]:
        if not query:
            return ()
        query = query.lower()
        results = []

        for side, doc in [("left", self.left_document), ("right", self.right_document)]:
            for p in doc.paragraphs:
                text_lower = p.text.lower()
                start = 0
                while True:
                    idx = text_lower.find(query, start)
                    if idx == -1:
                        break
                    results.append(SearchResult(
                        paragraph_index=p.index,
                        paragraph_id=p.paragraph_id,
                        char_start=idx,
                        char_end=idx + len(query),
                        document_side=side,
                    ))
                    start = idx + len(query)
        return tuple(results)

    def get_paragraph_by_id(self, paragraph_id: str) -> Optional[ReportParagraph]:
        for doc in (self.left_document, self.right_document):
            for p in doc.paragraphs:
                if p.paragraph_id == paragraph_id:
                    return p
        return None

    def get_match_by_id(self, match_id: int) -> Optional[ReportMatch]:
        for m in self.matches:
            if m.match_id == match_id:
                return m
        return None
