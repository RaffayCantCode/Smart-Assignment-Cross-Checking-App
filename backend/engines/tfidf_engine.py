from typing import Optional
from .base import ComparisonEngine, EngineCapabilities, EngineConfig, ProgressCallback
from ..domain.document import Document
from ..domain.comparison import ComparisonResult

class TFIDFEngine(ComparisonEngine):
    ENGINE_ID   = "tfidf_v1"
    ENGINE_NAME = "TF-IDF Vectorizer"

    @property
    def engine_id(self) -> str: return self.ENGINE_ID
    
    @property
    def engine_name(self) -> str: return self.ENGINE_NAME

    def is_available(self) -> bool:
        try:
            import sklearn
            return True
        except ImportError:
            return False

    @property
    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
            paragraph_matching=True,
            sentence_matching=False,
            span_matching=False,
            multilingual=False,
            offline=True,
            requires_gpu=False,
            approximate_time_per_para=0.001,
        )

    def compare(
        self,
        doc_a: Document,
        doc_b: Document,
        config: EngineConfig,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ComparisonResult:
        raise NotImplementedError("TFIDFEngine.compare() is not yet implemented.")
