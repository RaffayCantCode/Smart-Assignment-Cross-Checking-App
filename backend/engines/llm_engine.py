from typing import Optional
from .base import ComparisonEngine, EngineCapabilities, EngineConfig, ProgressCallback
from ..domain.document import Document
from ..domain.comparison import ComparisonResult

class LLMEngine(ComparisonEngine):
    ENGINE_ID   = "llm_v1"
    ENGINE_NAME = "LLM-Powered Analysis"

    @property
    def engine_id(self) -> str: return self.ENGINE_ID
    
    @property
    def engine_name(self) -> str: return self.ENGINE_NAME

    def is_available(self) -> bool:
        return False

    @property
    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
            paragraph_matching=True,
            sentence_matching=True,
            span_matching=True,
            multilingual=True,
            offline=False,
            requires_gpu=False,
            approximate_time_per_para=1.5,
        )

    def compare(
        self,
        doc_a: Document,
        doc_b: Document,
        config: EngineConfig,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ComparisonResult:
        raise NotImplementedError("LLMEngine requires API key configuration.")
