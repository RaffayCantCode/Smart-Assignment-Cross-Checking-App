import time
import re
import numpy as np
from typing import Optional

from .base import ComparisonEngine, EngineCapabilities, EngineConfig, ProgressCallback
from ..domain.document import Document
from ..domain.comparison import (
    ComparisonResult, SimilarityStatistics, SimilarityBand,
    MatchedParagraph, MatchedSentence, MatchedSpan
)


class TFIDFEngine(ComparisonEngine):
    ENGINE_ID   = "tfidf_v1"
    ENGINE_NAME = "TF-IDF Vectorizer"

    @property
    def engine_id(self) -> str:
        return self.ENGINE_ID

    @property
    def engine_name(self) -> str:
        return self.ENGINE_NAME

    def is_available(self) -> bool:
        import importlib.util
        return (
            importlib.util.find_spec("sklearn") is not None
            and importlib.util.find_spec("numpy") is not None
        )

    @property
    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
            paragraph_matching=True,
            sentence_matching=True,
            span_matching=True,
            multilingual=False,
            offline=True,
            requires_gpu=False,
            approximate_time_per_para=0.001,
        )

    def _match_sentences(self, para_a, para_b, config: EngineConfig) -> tuple[MatchedSentence, ...]:
        sents_a = para_a.sentences
        sents_b = para_b.sentences
        if not sents_a or not sents_b:
            return ()

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            texts_a = [s.text for s in sents_a]
            texts_b = [s.text for s in sents_b]

            vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
            all_texts = texts_a + texts_b
            tfidf_all = vectorizer.fit_transform(all_texts)
            emb_a = tfidf_all[:len(texts_a)]
            emb_b = tfidf_all[len(texts_a):]

            sim = cosine_similarity(emb_a, emb_b)

            matches = []
            for i, sa in enumerate(sents_a):
                row = sim[i]
                if len(row) == 0:
                    continue
                best_b = int(np.argmax(row))
                score = float(row[best_b])
                if score >= config.sentence_threshold:
                    sb = sents_b[best_b]
                    span = MatchedSpan(
                        char_start_a=sa.char_start,
                        char_end_a=sa.char_end,
                        char_start_b=sb.char_start,
                        char_end_b=sb.char_end,
                        text_a=sa.text,
                        text_b=sb.text,
                        similarity=score,
                    )
                    matches.append(MatchedSentence(
                        sentence_a=sa,
                        sentence_b=sb,
                        score=score,
                        spans=(span,),
                    ))
            return tuple(matches)
        except Exception:
            return ()

    def compare(
        self,
        doc_a: Document,
        doc_b: Document,
        config: EngineConfig,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ComparisonResult:
        start_time = time.time()

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            if progress_callback:
                progress_callback(10, "Extracting text vectors")

            paras_a = doc_a.paragraphs[:config.max_paragraphs] if config.max_paragraphs else doc_a.paragraphs
            paras_b = doc_b.paragraphs[:config.max_paragraphs] if config.max_paragraphs else doc_b.paragraphs

            texts_a = [p.text for p in paras_a]
            texts_b = [p.text for p in paras_b]

            if not texts_a or not texts_b:
                stats = SimilarityStatistics(
                    overall_score=0.0,
                    score_percent=0,
                    max_match_score=0.0,
                    min_match_score=0.0,
                    avg_match_score=0.0,
                    coverage_a=0.0,
                    coverage_b=0.0,
                    band=SimilarityBand.LOW,
                    confidence=0.90,
                )
                return ComparisonResult(
                    mode="one_to_one",
                    engine_id=self.ENGINE_ID,
                    doc_a=doc_a,
                    doc_b=doc_b,
                    statistics=stats,
                    matched_paragraphs=(),
                    unique_paragraphs_a=tuple(paras_a),
                    unique_paragraphs_b=tuple(paras_b),
                    metadata_warnings=(),
                    summary="No readable text available to compare.",
                    processing_time_s=time.time() - start_time,
                    error=False,
                    error_message=None,
                )

            if progress_callback:
                progress_callback(40, "Vectorizing paragraphs")

            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=1,
                sublinear_tf=True,
                token_pattern=r"(?u)\b\w+\b"
            )
            all_paras = texts_a + texts_b
            tfidf_all = vectorizer.fit_transform(all_paras)
            emb_a = tfidf_all[:len(texts_a)]
            emb_b = tfidf_all[len(texts_a):]

            if progress_callback:
                progress_callback(70, "Computing similarities")

            sim_matrix = cosine_similarity(emb_a, emb_b)

            matched_paras = []
            matched_indices1 = set()
            matched_indices2 = set()

            for i, row in enumerate(sim_matrix):
                if len(row) == 0:
                    continue
                best_idx = int(np.argmax(row))
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
                confidence=0.92
            )

            if progress_callback:
                progress_callback(100, "Done")

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
            return ComparisonResult.error_result(
                doc_a, doc_b, f"TF-IDF comparison error: {e}", self.ENGINE_ID, time.time() - start_time
            )
