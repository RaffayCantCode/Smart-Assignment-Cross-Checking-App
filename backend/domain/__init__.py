from .document import (
    ExtractionMethod,
    Sentence,
    Paragraph,
    ExtractionWarning,
    ExtractionInfo,
    DocumentSource,
    DocumentContent,
    Document,
)

from .comparison import (
    MatchedSpan,
    MatchedSentence,
    MatchedParagraph,
    SimilarityBand,
    MetadataWarning,
    SimilarityStatistics,
    ComparisonResult,
    MultiComparisonResult,
)

__all__ = [
    "ExtractionMethod",
    "Sentence",
    "Paragraph",
    "ExtractionWarning",
    "ExtractionInfo",
    "DocumentSource",
    "DocumentContent",
    "Document",
    "MatchedSpan",
    "MatchedSentence",
    "MatchedParagraph",
    "SimilarityBand",
    "MetadataWarning",
    "SimilarityStatistics",
    "ComparisonResult",
    "MultiComparisonResult",
]
