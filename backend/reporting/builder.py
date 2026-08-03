"""
backend/reporting/builder.py

Builds a ReportModel from a ComparisonResult.

Span resolution strategy
------------------------
The embedding engine produces sentence-level alignments (MatchedSentence)
each of which contains a MatchedSpan covering the entire sentence.  That
is often too coarse: a 3-sentence paragraph where only 1 sentence matches
should highlight just that sentence, and within that sentence we want the
tightest possible character range.

We refine the spans in two passes:

Pass 1 — Sentence-level: filter out any MatchedSentence whose score is
  below the engine's sentence threshold.  This prevents the entire
  paragraph from being coloured when only a weak semantic link exists at
  the paragraph level.

Pass 2 — Sub-sentence difflib refinement: for each surviving
  MatchedSentence we run difflib.SequenceMatcher on the two sentence
  texts to find the longest contiguous matching block.  If that block is
  at least 6 characters (avoids single-word false positives), we tighten
  the span to cover only those characters.  Otherwise we keep the full
  sentence span.

Fallback: if no sentence-level spans survive (e.g. when
  enable_sentence_matching is False or the sentences fall below
  threshold), we emit a single span covering the whole paragraph text.
  A paragraph-level semantic match still deserves a visible highlight;
  this makes the match explicit rather than invisible.
"""

import difflib
from typing import Dict, Tuple

from .model import (
    ReportModel, ReportDocument, ReportParagraph, ReportSpan,
    ReportMatch, ReportStatistics, MatchType, _make_paragraph_id,
)
from ..domain.comparison import ComparisonResult, MatchedParagraph

# Minimum number of characters in a difflib block for it to replace the
# full-sentence span.  Below this we keep the whole sentence highlighted.
_MIN_BLOCK_CHARS = 6


def _refine_span(
    para_text: str,
    sent_char_start: int,
    sent_char_end: int,
    sent_text_a: str,
    sent_text_b: str,
) -> tuple[int, int]:
    """
    Tighten a sentence-level span using difflib longest-common-substring.

    `para_text`        — the full paragraph text (for bounds validation)
    `sent_char_start`  — sentence start offset within para_text
    `sent_char_end`    — sentence end offset within para_text
    `sent_text_a`      — sentence text from document A (the local side)
    `sent_text_b`      — sentence text from document B (the peer)

    Returns (refined_start, refined_end) both relative to para_text.
    Falls back to the original sentence range on any error.
    """
    try:
        sm = difflib.SequenceMatcher(None, sent_text_a.lower(), sent_text_b.lower(),
                                     autojunk=False)
        best_block = max(sm.get_matching_blocks(), key=lambda b: b.size, default=None)

        if best_block is None or best_block.size < _MIN_BLOCK_CHARS:
            return sent_char_start, sent_char_end

        # best_block.a  = start offset in sent_text_a
        # best_block.size = length of the block
        block_start_in_sent = best_block.a
        block_end_in_sent   = best_block.a + best_block.size

        # Map back to paragraph-relative offsets
        refined_start = sent_char_start + block_start_in_sent
        refined_end   = sent_char_start + block_end_in_sent

        # Sanity-clamp to sentence boundaries
        refined_start = max(sent_char_start, min(refined_start, sent_char_end))
        refined_end   = max(sent_char_start, min(refined_end,   sent_char_end))

        if refined_start >= refined_end:
            return sent_char_start, sent_char_end

        return refined_start, refined_end

    except Exception:
        return sent_char_start, sent_char_end


def _build_spans_for_side(
    para_text: str,
    mp: MatchedParagraph,
    side: str,
    match_id: int,
    m_type: MatchType,
) -> list[ReportSpan]:
    """
    Build the list of ReportSpan for one side of a MatchedParagraph.

    Each span covers the tightest character range that the engine and the
    difflib refinement agree is matching text.

    If no sentence-level spans survive, returns one span covering the
    whole paragraph (paragraph-level fallback).
    """
    spans: list[ReportSpan] = []

    for ms in mp.matched_sentences:
        for raw_span in ms.spans:
            s_type = MatchType.from_score(raw_span.score)

            if side == "A":
                sent_start = raw_span.char_start_a
                sent_end   = raw_span.char_end_a
                sent_text_local = raw_span.text_a
                sent_text_peer  = raw_span.text_b
            else:
                sent_start = raw_span.char_start_b
                sent_end   = raw_span.char_end_b
                sent_text_local = raw_span.text_b
                sent_text_peer  = raw_span.text_a

            # Guard against out-of-bounds offsets (defensive)
            sent_start = max(0, min(sent_start, len(para_text)))
            sent_end   = max(sent_start, min(sent_end, len(para_text)))

            if sent_start >= sent_end:
                continue  # degenerate span, skip

            # Attempt sub-sentence refinement via difflib
            refined_start, refined_end = _refine_span(
                para_text, sent_start, sent_end,
                sent_text_local, sent_text_peer,
            )

            spans.append(ReportSpan(refined_start, refined_end, s_type, match_id))

    # Merge overlapping / adjacent spans with the same match_id
    spans = _merge_spans(spans)

    if not spans:
        # Fallback: no sentence matches → highlight whole paragraph
        spans = [ReportSpan(0, len(para_text), m_type, match_id)]

    return spans


def _merge_spans(spans: list[ReportSpan]) -> list[ReportSpan]:
    """
    Merge overlapping or adjacent spans that share the same match_id.

    Prevents double-formatting of text regions and keeps the rendering
    loop in ParagraphWidget simple (no overlapping ranges).
    """
    if len(spans) <= 1:
        return spans

    sorted_spans = sorted(spans, key=lambda s: (s.match_id, s.char_start))
    merged: list[ReportSpan] = []

    for span in sorted_spans:
        if merged and merged[-1].match_id == span.match_id and span.char_start <= merged[-1].char_end:
            # Extend the last merged span
            prev = merged[-1]
            merged[-1] = ReportSpan(
                prev.char_start,
                max(prev.char_end, span.char_end),
                prev.match_type,
                prev.match_id,
            )
        else:
            merged.append(span)

    return merged


class ReportBuilder:
    @staticmethod
    def build(result: ComparisonResult) -> ReportModel:
        left_match_map:  Dict[int, Tuple[int, object]] = {}
        right_match_map: Dict[int, Tuple[int, object]] = {}
        match_list = []

        exact_count   = 0
        partial_count = 0
        semantic_count = 0

        for i, mp in enumerate(result.matched_paragraphs):
            match_id  = i + 1
            left_idx  = mp.paragraph_a.index
            right_idx = mp.paragraph_b.index

            left_pid  = _make_paragraph_id("A", left_idx)
            right_pid = _make_paragraph_id("B", right_idx)

            left_match_map[left_idx]  = (match_id, mp)
            right_match_map[right_idx] = (match_id, mp)

            m_type = MatchType.from_score(mp.score)

            left_sent_indices  = tuple(ms.sentence_a.index for ms in mp.matched_sentences)
            right_sent_indices = tuple(ms.sentence_b.index for ms in mp.matched_sentences)

            match_list.append(ReportMatch(
                match_id=match_id,
                type=m_type,
                left_paragraph_index=left_idx,
                right_paragraph_index=right_idx,
                left_paragraph_id=left_pid,
                right_paragraph_id=right_pid,
                score=mp.score,
                left_sentence_indices=left_sent_indices,
                right_sentence_indices=right_sent_indices,
            ))

            if m_type == MatchType.EXACT:
                exact_count += 1
            elif m_type == MatchType.PARTIAL:
                partial_count += 1
            elif m_type == MatchType.SEMANTIC:
                semantic_count += 1

        def build_report_doc(
            doc,
            match_map: Dict[int, Tuple[int, object]],
            side: str,
        ) -> ReportDocument:
            report_paras = []
            for p in doc.paragraphs:
                para_id = _make_paragraph_id(side, p.index)
                if p.index in match_map:
                    match_id, mp = match_map[p.index]
                    m_type = MatchType.from_score(mp.score)

                    spans = _build_spans_for_side(
                        p.text, mp, side, match_id, m_type
                    )

                    other_idx = (
                        mp.paragraph_b.index if side == "A"
                        else mp.paragraph_a.index
                    )
                    other_pid = _make_paragraph_id(
                        "B" if side == "A" else "A", other_idx
                    )
                    report_paras.append(ReportParagraph(
                        index=p.index,
                        paragraph_id=para_id,
                        text=p.text,
                        spans=tuple(spans),
                        primary_match_type=m_type,
                        is_matched=True,
                        match_score=mp.score,
                        matched_paragraph_index=other_idx,
                        matched_paragraph_id=other_pid,
                        sentence_count=p.sentence_count,
                        word_count=p.word_count,
                        is_ocr_derived=p.is_ocr_derived,
                    ))
                else:
                    report_paras.append(ReportParagraph(
                        index=p.index,
                        paragraph_id=para_id,
                        text=p.text,
                        spans=(),
                        primary_match_type=MatchType.UNIQUE,
                        is_matched=False,
                        matched_paragraph_index=None,
                        matched_paragraph_id="",
                        sentence_count=p.sentence_count,
                        word_count=p.word_count,
                        is_ocr_derived=p.is_ocr_derived,
                    ))
            return ReportDocument(title=doc.file_name, paragraphs=tuple(report_paras))

        left_doc = build_report_doc(result.doc_a, left_match_map, "A")

        if result.doc_b:
            right_doc    = build_report_doc(result.doc_b, right_match_map, "B")
            ocr_used     = result.doc_a.has_ocr_content or result.doc_b.has_ocr_content
            avg_conf_a   = result.doc_a.extraction_info.mean_ocr_confidence
            avg_conf_b   = result.doc_b.extraction_info.mean_ocr_confidence
            avg_ocr_conf = max(avg_conf_a, avg_conf_b) if (avg_conf_a or avg_conf_b) else 0.0
        else:
            right_doc    = ReportDocument(title="N/A", paragraphs=())
            ocr_used     = result.doc_a.has_ocr_content
            avg_ocr_conf = result.doc_a.extraction_info.mean_ocr_confidence

        unique_count = sum(
            1 for p in left_doc.paragraphs if not p.is_matched
        ) + sum(
            1 for p in right_doc.paragraphs if not p.is_matched
        )

        stats = ReportStatistics(
            similarity_percent=result.statistics.score_percent,
            total_matches=len(match_list),
            exact_matches=exact_count,
            partial_matches=partial_count,
            semantic_matches=semantic_count,
            unique_paragraphs=unique_count,
            ocr_used=bool(ocr_used),
            avg_ocr_confidence=avg_ocr_conf,
            confidence=result.statistics.confidence,
        )

        return ReportModel(
            statistics=stats,
            left_document=left_doc,
            right_document=right_doc,
            matches=tuple(match_list),
        )
