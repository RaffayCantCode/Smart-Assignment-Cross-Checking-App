from dataclasses import dataclass
from enum import Enum
from typing import Optional

class MatchType(str, Enum):
    EXACT = "exact"
    PARTIAL = "partial"
    SEMANTIC = "semantic"
    NONE = "none"

    @classmethod
    def from_score(cls, score: float) -> 'MatchType':
        if score >= 0.95:
            return cls.EXACT
        elif score >= 0.70:
            return cls.PARTIAL
        elif score >= 0.40:
            return cls.SEMANTIC
        return cls.NONE

@dataclass(frozen=True)
class ReportSpan:
    char_start: int
    char_end: int
    match_type: MatchType
    match_id: int

@dataclass(frozen=True)
class ReportParagraph:
    index: int
    text: str
    spans: tuple[ReportSpan, ...]
    primary_match_type: MatchType
    is_matched: bool
    matched_paragraph_index: Optional[int] = None

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
    score: float

@dataclass(frozen=True)
class ReportStatistics:
    similarity_percent: int
    total_matches: int
    exact_matches: int
    partial_matches: int
    semantic_matches: int
    ocr_used: bool

@dataclass(frozen=True)
class SearchResult:
    paragraph_index: int
    char_start: int
    char_end: int
    document_side: str # "left" or "right"

@dataclass(frozen=True)
class ReportModel:
    statistics: ReportStatistics
    left_document: ReportDocument
    right_document: ReportDocument
    matches: tuple[ReportMatch, ...]
    
    def search(self, query: str) -> tuple[SearchResult, ...]:
        """Simple case-insensitive search index returning all occurrences."""
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
                    results.append(SearchResult(p.index, idx, idx + len(query), side))
                    start = idx + len(query)
        return tuple(results)
