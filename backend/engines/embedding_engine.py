import time
import threading
import numpy as np
from typing import Optional

from .base import ComparisonEngine, EngineCapabilities, EngineConfig, ProgressCallback
from ..domain.document import Document
from ..domain.comparison import (
    ComparisonResult, SimilarityStatistics, SimilarityBand,
    MatchedParagraph, MatchedSentence, MatchedSpan
)

class EmbeddingEngine(ComparisonEngine):
    ENGINE_ID   = "embedding_v1"
    ENGINE_NAME = "Sentence Embedding (MiniLM-L6)"
    MODEL_NAME  = "all-MiniLM-L6-v2"

    _shared_model = None
    _embedding_cache = {}
    _load_lock = threading.Lock()

    def __init__(self):
        pass

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
            approximate_time_per_para=0.005,
        )

    def is_available(self) -> bool:
        # Fast availability check - uses find_spec (no heavy torch import here).
        # The actual model + dependencies are imported lazily inside compare().
        import importlib.util
        return (
            importlib.util.find_spec("sentence_transformers") is not None
            and importlib.util.find_spec("sklearn") is not None
        )

    def _ensure_model_loaded(self) -> None:
        if EmbeddingEngine._shared_model is None:
            with EmbeddingEngine._load_lock:
                if EmbeddingEngine._shared_model is None:
                    import os
                    import sys
                    from sentence_transformers import SentenceTransformer
                    
                    # Check for bundled local model in assets/models/all-MiniLM-L6-v2
                    base_dirs = [
                        getattr(sys, '_MEIPASS', ''),
                        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')),
                        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '_internal')),
                    ]
                    local_model_path = None
                    for b in base_dirs:
                        if b:
                            p = os.path.join(b, "assets", "models", "all-MiniLM-L6-v2")
                            if os.path.isdir(p) and os.path.isfile(os.path.join(p, "config.json")):
                                local_model_path = p
                                break

                    target = local_model_path if local_model_path else self.MODEL_NAME
                    EmbeddingEngine._shared_model = SentenceTransformer(target)

    def _get_embeddings(self, texts: list[str], config: EngineConfig) -> np.ndarray:
        if not texts:
            return np.array([])

        if not config.enable_cache:
            return EmbeddingEngine._shared_model.encode(
                texts,
                batch_size=config.batch_size,
                show_progress_bar=False
            )

        cached_vectors = []
        missing_indices = []
        missing_texts = []

        for i, text in enumerate(texts):
            if text in EmbeddingEngine._embedding_cache:
                cached_vectors.append((i, EmbeddingEngine._embedding_cache[text]))
            else:
                missing_indices.append(i)
                missing_texts.append(text)

        if missing_texts:
            new_embeds = EmbeddingEngine._shared_model.encode(
                missing_texts,
                batch_size=config.batch_size,
                show_progress_bar=False
            )
            for text, vec in zip(missing_texts, new_embeds):
                EmbeddingEngine._embedding_cache[text] = vec
            for idx, vec in zip(missing_indices, new_embeds):
                cached_vectors.append((idx, vec))

        cached_vectors.sort(key=lambda x: x[0])
        return np.array([v for _, v in cached_vectors])

    def _match_sentences(self, para_a, para_b, config: EngineConfig) -> tuple[MatchedSentence, ...]:
        """Compares the sentences of two matched paragraphs and returns the
        sentence pairs grouped above the sentence threshold. Each matched
        sentence exposes a character span (paragraph-relative) so the report
        can highlight the actually-matching text within a paragraph."""
        sents_a = para_a.sentences
        sents_b = para_b.sentences
        if not sents_a or not sents_b:
            return ()

        try:
            from sklearn.metrics.pairwise import cosine_similarity

            texts_a = [s.text for s in sents_a]
            texts_b = [s.text for s in sents_b]
            emb_a = self._get_embeddings(texts_a, config)
            emb_b = self._get_embeddings(texts_b, config)
            if len(emb_a) == 0 or len(emb_b) == 0:
                return ()
            sim = cosine_similarity(emb_a, emb_b)

            matches = []
            matched_b = set()
            for i, sa in enumerate(sents_a):
                row = sim[i]
                if len(row) == 0:
                    continue
                j = int(np.argmax(row))
                score = float(row[j])
                if score >= config.sentence_threshold and j not in matched_b:
                    sb = sents_b[j]
                    matched_b.add(j)
                    span = MatchedSpan(
                        text_a=sa.text,
                        text_b=sb.text,
                        score=score,
                        char_start_a=sa.char_start,
                        char_end_a=sa.char_end,
                        char_start_b=sb.char_start,
                        char_end_b=sb.char_end,
                    )
                    matches.append(MatchedSentence(
                        sentence_a=sa,
                        sentence_b=sb,
                        score=score,
                        spans=(span,),
                    ))
            return tuple(matches)
        except Exception:
            # Sentence-level matching is best-effort; fall back to no spans
            # so a failure here never aborts the whole comparison.
            return ()

    def compare(
        self,
        doc_a: Document,
        doc_b: Document,
        config: EngineConfig,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ComparisonResult:
        start_time = time.time()

        if progress_callback:
            progress_callback(2, "Loading AI model (first run may take a while to download)")

        try:
            self._ensure_model_loaded()
        except Exception as e:
            # Automatic graceful fallback to TF-IDF Engine so comparisons always work
            from .tfidf_engine import TFIDFEngine
            fallback_engine = TFIDFEngine()
            if progress_callback:
                progress_callback(5, "Analyzing with text similarity engine")
            return fallback_engine.compare(doc_a, doc_b, config, progress_callback)

        if progress_callback:
            progress_callback(3, "AI model ready")

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            
            if progress_callback: progress_callback(10, "Encoding document 1")
            paras_a = doc_a.paragraphs[:config.max_paragraphs] if config.max_paragraphs else doc_a.paragraphs
            texts_a = [p.text for p in paras_a]
            embeds_a = self._get_embeddings(texts_a, config) if texts_a else np.array([])
            
            if progress_callback: progress_callback(40, "Encoding document 2")
            paras_b = doc_b.paragraphs[:config.max_paragraphs] if config.max_paragraphs else doc_b.paragraphs
            texts_b = [p.text for p in paras_b]
            embeds_b = self._get_embeddings(texts_b, config) if texts_b else np.array([])

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
                    if config.enable_sentence_matching:
                        matched_sentences = self._match_sentences(
                            paras_a[i], paras_b[best_idx], config
                        )
                    else:
                        matched_sentences = ()
                    
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
            try:
                from .tfidf_engine import TFIDFEngine
                return TFIDFEngine().compare(doc_a, doc_b, config, progress_callback)
            except Exception:
                return ComparisonResult.error_result(doc_a, doc_b, f"Comparison error: {e}", self.ENGINE_ID, time.time() - start_time)


def preload_model() -> None:
    """Loads the shared embedding model once. Safe to call from a background
    thread at app startup so analyses don't stall on first use."""
    engine = EmbeddingEngine()
    engine._ensure_model_loaded()
