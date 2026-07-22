from backend.domain.document import Document, DocumentSource, DocumentContent, ExtractionInfo, ExtractionMethod, Paragraph, Sentence
from backend.domain.comparison import ComparisonResult, SimilarityStatistics, SimilarityBand, MatchedParagraph, MatchedSentence, MatchedSpan
from backend.reporting.builder import ReportBuilder
from backend.reporting.model import MatchType

def create_dummy_doc(filename: str, paras: list[str]) -> Document:
    paragraphs = []
    total_words = 0
    total_sents = 0
    for i, p_text in enumerate(paras):
        words = p_text.split()
        total_words += len(words)
        
        # very naive sentence splitting
        sents = p_text.split(". ")
        sentences = []
        offset = 0
        for j, s_text in enumerate(sents):
            if not s_text.endswith("."):
                s_text += "." if j < len(sents) - 1 else ""
            idx = p_text.find(s_text, offset)
            sentences.append(Sentence(s_text, j, idx, idx + len(s_text)))
            offset = idx + len(s_text)
            total_sents += 1
            
        paragraphs.append(Paragraph(p_text, i, 1, len(words), len(p_text), False, tuple(sentences)))
        
    content = DocumentContent("\n".join(paras), tuple(paragraphs), total_words, len(paragraphs), total_sents)
    source = DocumentSource(filename, filename, ".txt", 100, 0.0)
    info = ExtractionInfo(ExtractionMethod.DIGITAL_TEXT, 1, 0, 0.1, ())
    return Document(source, content, info)

def test_builder():
    print("Testing ReportBuilder...")
    doc_a = create_dummy_doc("doc_a.txt", ["Hello world.", "This is a test paragraph.", "Unique text here."])
    doc_b = create_dummy_doc("doc_b.txt", ["Hello world.", "This is a similar paragraph.", "Different text here."])
    
    # Create fake match
    span = MatchedSpan("This is a test paragraph.", "This is a similar paragraph.", 0.85, 0, 25, 0, 28)
    ms = MatchedSentence(doc_a.paragraphs[1].sentences[0], doc_b.paragraphs[1].sentences[0], 0.85, (span,))
    mp = MatchedParagraph(doc_a.paragraphs[1], doc_b.paragraphs[1], 0.85, (ms,))
    
    span2 = MatchedSpan("Hello world.", "Hello world.", 1.0, 0, 12, 0, 12)
    ms2 = MatchedSentence(doc_a.paragraphs[0].sentences[0], doc_b.paragraphs[0].sentences[0], 1.0, (span2,))
    mp2 = MatchedParagraph(doc_a.paragraphs[0], doc_b.paragraphs[0], 1.0, (ms2,))
    
    stats = SimilarityStatistics(0.6, 60, 1.0, 0.85, 0.92, 0.66, 0.66, SimilarityBand.MEDIUM, 0.9)
    result = ComparisonResult("one_to_one", "test", doc_a, doc_b, stats, (mp2, mp), (), (), (), "Test summary", 0.5)
    
    model = ReportBuilder.build(result)
    
    assert model.statistics.similarity_percent == 60
    assert model.statistics.exact_matches == 1
    assert model.statistics.partial_matches == 1
    assert model.statistics.semantic_matches == 0
    assert len(model.matches) == 2
    
    assert model.left_document.paragraphs[0].primary_match_type == MatchType.EXACT
    assert model.left_document.paragraphs[1].primary_match_type == MatchType.PARTIAL
    assert model.left_document.paragraphs[2].primary_match_type == MatchType.NONE
    
    assert model.left_document.paragraphs[0].is_matched == True
    assert model.left_document.paragraphs[1].is_matched == True
    assert model.left_document.paragraphs[2].is_matched == False
    
    # Test Search
    search_results = model.search("world")
    assert len(search_results) == 2
    assert search_results[0].paragraph_index == 0
    assert search_results[0].document_side == "left"
    
    print("All tests passed!")

if __name__ == "__main__":
    test_builder()
