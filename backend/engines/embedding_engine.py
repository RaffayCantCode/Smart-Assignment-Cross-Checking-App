import time
import numpy as np
from typing import Optional

from .base import ComparisonEngine, EngineCapabilities, EngineConfig, ProgressCallback
from ..domain.document import Document
from ..domain.comparison import (
    ComparisonResult, SimilarityStatistics, SimilarityBand,
    MatchedParagraph, MatchedSentence
)

class EmbeddingEngine(ComparisonEngine):
    ENGINE_ID   = "embedding_v1"
    ENGINE_NAME = "Sentence Embedding (MiniLM-L6)"
    MODEL_NAME  = "all-MiniLM-L6-v2"

    def __init__(self):
        self._model = None

    @property
    def engine_id(self) -> str: return self.ENGINE_ID
    
    @property
    def engine_name(self) -> str: return self.ENGINE_NAME

    @property
    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
            paragraph_matching=True,
            sentence_matching=True,
            span_matching=False,
            multilingual=False,
            offline=True,
            requires_gpu=False,
            approximate_time_per_para=0.02,
        )

    def is_available(self) -> bool:
        try:
            import sentence_transformers
            import sklearn
            return True
        except ImportError:
            return False

    def _ensure_model_loaded(self) -> None:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.MODEL_NAME)

    def compare(
        self,
        doc_a: Document,
        doc_b: Document,
        config: EngineConfig,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ComparisonResult:
        start_time = time.time()
        
        try:
            self._ensure_model_loaded()
        except Exception as e:
            return ComparisonResult.error_result(doc_a, doc_b, f"Failed to load model: {e}", self.ENGINE_ID, time.time() - start_time)

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            
            if progress_callback: progress_callback(10, "Encoding document 1")
            paras_a = doc_a.paragraphs
            texts_a = [p.text for p in paras_a]
            embeds_a = self._model.encode(texts_a, show_progress_bar=False) if texts_a else np.array([])
            
            if progress_callback: progress_callback(40, "Encoding document 2")
            paras_b = doc_b.paragraphs
            texts_b = [p.text for p in paras_b]
            embeds_b = self._model.encode(texts_b, show_progress_bar=False) if texts_b else np.array([])

            if progress_callback: progress_callback(70, "Computing similarities")
            
            if len(embeds_a) == 0 or len(embeds_b) == 0:
                sim_matrix = np.array([[]])
            else:
                sim_matrix = cosine_similarity(embeds_a, embeds_b)

            matched_paras = []
            matched_indices1 = set()
            matched_indices2 = set()

            for i, row in enumerate(sim_matrix):
                if len(row) == 0: continue
                best_idx = np.argmax(row)
                best_score = float(row[best_idx])
                
                if best_score >= config.similarity_threshold:
                    matched_sentences = ()
                    # Phase 2 will implement optional sentence level matching
                    
                    matched_paras.append(MatchedParagraph(
                        paragraph_a=paras_a[i],
                        paragraph_b=paras_b[best_idx],
                        score=best_score,
                        matched_sentences=matched_sentences
                    ))
                    matched_indices1.add(i)
                    matched_indices2.add(best_idx)

            matched_paras.sort(key=lambda x: x.score, reverse=True)

            unique_a = [p for i, p in enumerate(paras_a) if i not in matched_indices1]
            unique_b = [p for i, p in enumerate(paras_b) if i not in matched_indices2]

            total_matched = len(matched_indices1) + len(matched_indices2)
            total_paras = len(paras_a) + len(paras_b)
            
            coverage = total_matched / total_paras if total_paras > 0 else 0
            avg_match_score = sum(m.score for m in matched_paras) / len(matched_paras) if matched_paras else 0.0
            overall_score = coverage * avg_match_score
            
            max_match_score = max((m.score for m in matched_paras), default=0.0)
            min_match_score = min((m.score for m in matched_paras), default=0.0)
            
            cov_a = len(matched_indices1) / len(paras_a) if len(paras_a) > 0 else 0.0
            cov_b = len(matched_indices2) / len(paras_b) if len(paras_b) > 0 else 0.0
            
            stats = SimilarityStatistics(
                overall_score=overall_score,
                score_percent=min(100, int(overall_score * 100)),
                max_match_score=max_match_score,
                min_match_score=min_match_score,
                avg_match_score=avg_match_score,
                coverage_a=cov_a,
                coverage_b=cov_b,
                band=SimilarityBand.from_score(overall_score),
                confidence=0.95
            )

            if progress_callback: progress_callback(100, "Done")

            return ComparisonResult(
                mode="one_to_one",
                engine_id=self.ENGINE_ID,
                doc_a=doc_a,
                doc_b=doc_b,
                statistics=stats,
                matched_paragraphs=tuple(matched_paras),
                unique_paragraphs_a=tuple(unique_a),
                unique_paragraphs_b=tuple(unique_b),
                metadata_warnings=(),
                summary="",
                processing_time_s=time.time() - start_time,
                error=False,
                error_message=None
            )
        except Exception as e:
            return ComparisonResult.error_result(doc_a, doc_b, f"Comparison error: {e}", self.ENGINE_ID, time.time() - start_time)
