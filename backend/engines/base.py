from typing import Protocol, runtime_checkable, Callable, Optional
from dataclasses import dataclass
from ..domain.document import Document
from ..domain.comparison import ComparisonResult

ProgressCallback = Callable[[int, str], None]

@dataclass(frozen=True)
class EngineCapabilities:
    paragraph_matching: bool
    sentence_matching: bool
    span_matching: bool
    multilingual: bool
    offline: bool
    requires_gpu: bool
    approximate_time_per_para: float

@dataclass(frozen=True)
class EngineConfig:
    similarity_threshold: float = 0.75
    sentence_threshold: float = 0.80
    enable_sentence_matching: bool = False
    max_paragraphs: int = 300
    batch_size: int = 64

@runtime_checkable
class ComparisonEngine(Protocol):
    @property
    def engine_id(self) -> str:
        ...

    @property
    def engine_name(self) -> str:
        ...

    @property
    def capabilities(self) -> EngineCapabilities:
        ...

    def is_available(self) -> bool:
        ...

    def compare(
        self,
        doc_a: Document,
        doc_b: Document,
        config: EngineConfig,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ComparisonResult:
        ...
