from enum import Enum
from dataclasses import dataclass
from typing import Optional

from .document import Document, Paragraph, Sentence

@dataclass(frozen=True)
class MatchedSpan:
    text_a: str
    text_b: str
    score: float
    char_start_a: int
    char_end_a: int
    char_start_b: int
    char_end_b: int

@dataclass(frozen=True)
class MatchedSentence:
    sentence_a: Sentence
    sentence_b: Sentence
    score: float
    spans: tuple[MatchedSpan, ...]

@dataclass(frozen=True)
class MatchedParagraph:
    paragraph_a: Paragraph
    paragraph_b: Paragraph
    score: float
    matched_sentences: tuple[MatchedSentence, ...]

    @property
    def score_percent(self) -> int:
        return min(100, int(self.score * 100))

class SimilarityBand(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"
    ERROR  = "error"

    @classmethod
    def from_score(cls, score: float) -> 'SimilarityBand':
        if score >= 0.70:
            return cls.HIGH
        elif score >= 0.40:
            return cls.MEDIUM
        else:
            return cls.LOW

    @property
    def label(self) -> str:
        return {
            "high":   "High Similarity",
            "medium": "Moderate Similarity",
            "low":    "Low Similarity",
            "error":  "Error",
        }[self.value]

    @property
    def hex_color(self) -> str:
        return {
            "high":   "#E63946",
            "medium": "#F4A261",
            "low":    "#2A9D8F",
            "error":  "#E63946",
        }[self.value]

@dataclass(frozen=True)
class MetadataWarning:
    code: str
    severity: str
    message: str

@dataclass(frozen=True)
class SimilarityStatistics:
    overall_score: float
    score_percent: int
    max_match_score: float
    min_match_score: float
    avg_match_score: float
    coverage_a: float
    coverage_b: float
    band: SimilarityBand
    confidence: float

    @classmethod
    def zero(cls) -> 'SimilarityStatistics':
        return cls(
            overall_score=0.0, score_percent=0,
            max_match_score=0.0, min_match_score=0.0, avg_match_score=0.0,
            coverage_a=0.0, coverage_b=0.0,
            band=SimilarityBand.LOW, confidence=0.0
        )

@dataclass(frozen=True)
class ComparisonResult:
    mode: str
    engine_id: str
    doc_a: Document
    doc_b: Optional[Document]

    statistics: SimilarityStatistics
    matched_paragraphs: tuple[MatchedParagraph, ...]
    unique_paragraphs_a: tuple[Paragraph, ...]
    unique_paragraphs_b: tuple[Paragraph, ...]
    metadata_warnings: tuple[MetadataWarning, ...]
    summary: str

    processing_time_s: float
    error: bool = False
    error_message: Optional[str] = None

    @property
    def risk_level(self) -> str:
        return self.statistics.band.label

    @property
    def risk_color(self) -> str:
        return self.statistics.band.hex_color

    @property
    def score_percent(self) -> int:
        return self.statistics.score_percent

    def to_legacy_dict(self) -> dict:
        return {
            "score":             self.statistics.score_percent,
            "risk_level":        self.risk_level,
            "risk_color":        self.risk_color,
            "matching_sections": len(self.matched_paragraphs),
            "similar_paragraphs": len(self.matched_paragraphs),
            "processing_time":   f"{self.processing_time_s:.1f}s",
            "confidence_score":  f"{int(self.statistics.confidence * 100)}%",
            "summary":           self.summary,
            "error":             self.error,
        }

    @classmethod
    def error_result(
        cls,
        doc_a: Document,
        doc_b: Optional[Document],
        message: str,
        engine_id: str = "unknown",
        processing_time_s: float = 0.0,
    ) -> 'ComparisonResult':
        return cls(
            mode="one_to_one",
            engine_id=engine_id,
            doc_a=doc_a,
            doc_b=doc_b,
            statistics=SimilarityStatistics.zero(),
            matched_paragraphs=(),
            unique_paragraphs_a=(),
            unique_paragraphs_b=(),
            metadata_warnings=(),
            summary=f"Processing failed: {message}",
            processing_time_s=processing_time_s,
            error=True,
            error_message=message,
        )

@dataclass(frozen=True)
class MultiComparisonResult:
    mode: str = "one_to_many"
    main_doc: Optional[Document] = None
    pairs: tuple[ComparisonResult, ...] = ()

    highest_score_percent: int = 0
    average_score_percent: int = 0
    overall_band: SimilarityBand = SimilarityBand.LOW
    overall_summary: str = ""
    total_processing_time_s: float = 0.0

    error: bool = False
    error_message: Optional[str] = None

    def to_legacy_dict(self) -> dict:
        return {
            "score":             self.highest_score_percent,
            "risk_level":        self.overall_band.label,
            "risk_color":        self.overall_band.hex_color,
            "matching_sections": sum(len(p.matched_paragraphs) for p in self.pairs),
            "similar_paragraphs": sum(len(p.matched_paragraphs) for p in self.pairs),
            "processing_time":   f"{self.total_processing_time_s:.1f}s",
            "confidence_score":  "N/A",
            "summary":           self.overall_summary,
            "error":             self.error,
            "pairs":             [p.to_legacy_dict() for p in self.pairs],
        }
