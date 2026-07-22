from typing import Dict
from .model import (
    ReportModel, ReportDocument, ReportParagraph, ReportSpan, 
    ReportMatch, ReportStatistics, MatchType
)
from ..domain.comparison import ComparisonResult

class ReportBuilder:
    @staticmethod
    def build(result: ComparisonResult) -> ReportModel:
        left_match_map: Dict[int, tuple] = {}
        right_match_map: Dict[int, tuple] = {}
        match_list = []
        
        exact_count = 0
        partial_count = 0
        semantic_count = 0
        
        for i, mp in enumerate(result.matched_paragraphs):
            match_id = i + 1
            left_idx = mp.paragraph_a.index
            right_idx = mp.paragraph_b.index
            
            # Map index to match details
            left_match_map[left_idx] = (match_id, mp)
            right_match_map[right_idx] = (match_id, mp)
            
            m_type = MatchType.from_score(mp.score)
            match_list.append(ReportMatch(
                match_id=match_id,
                type=m_type,
                left_paragraph_index=left_idx,
                right_paragraph_index=right_idx,
                score=mp.score
            ))
            
            if m_type == MatchType.EXACT:
                exact_count += 1
            elif m_type == MatchType.PARTIAL:
                partial_count += 1
            elif m_type == MatchType.SEMANTIC:
                semantic_count += 1
                
        def build_report_doc(doc, match_map: Dict[int, tuple], is_left: bool) -> ReportDocument:
            report_paras = []
            for p in doc.paragraphs:
                if p.index in match_map:
                    match_id, mp = match_map[p.index]
                    m_type = MatchType.from_score(mp.score)
                    
                    spans = []
                    for ms in mp.matched_sentences:
                        for span in ms.spans:
                            s_type = MatchType.from_score(span.score)
                            if is_left:
                                spans.append(ReportSpan(span.char_start_a, span.char_end_a, s_type, match_id))
                            else:
                                spans.append(ReportSpan(span.char_start_b, span.char_end_b, s_type, match_id))
                                
                    other_idx = mp.paragraph_b.index if is_left else mp.paragraph_a.index
                    report_paras.append(ReportParagraph(
                        index=p.index,
                        text=p.text,
                        spans=tuple(spans),
                        primary_match_type=m_type,
                        is_matched=True,
                        matched_paragraph_index=other_idx
                    ))
                else:
                    report_paras.append(ReportParagraph(
                        index=p.index,
                        text=p.text,
                        spans=(),
                        primary_match_type=MatchType.NONE,
                        is_matched=False,
                        matched_paragraph_index=None
                    ))
            return ReportDocument(title=doc.file_name, paragraphs=tuple(report_paras))
            
        left_doc = build_report_doc(result.doc_a, left_match_map, is_left=True)
        
        if result.doc_b:
            right_doc = build_report_doc(result.doc_b, right_match_map, is_left=False)
            ocr_used = result.doc_a.has_ocr_content or result.doc_b.has_ocr_content
        else:
            right_doc = ReportDocument(title="N/A", paragraphs=())
            ocr_used = result.doc_a.has_ocr_content
        
        stats = ReportStatistics(
            similarity_percent=result.statistics.score_percent,
            total_matches=len(match_list),
            exact_matches=exact_count,
            partial_matches=partial_count,
            semantic_matches=semantic_count,
            ocr_used=bool(ocr_used)
        )
        
        return ReportModel(
            statistics=stats,
            left_document=left_doc,
            right_document=right_doc,
            matches=tuple(match_list)
        )
