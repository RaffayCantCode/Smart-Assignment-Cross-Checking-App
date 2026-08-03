import time
from backend.engines.embedding_engine import EmbeddingEngine
from backend.engines.base import EngineConfig
from backend.domain.document import Document, DocumentSource, DocumentContent, Paragraph, Sentence, ExtractionInfo, ExtractionMethod

def make_dummy_doc(num_paras: int, prefix: str) -> Document:
    paras = []
    for i in range(num_paras):
        text = f"{prefix} Paragraph {i}: Machine learning models use gradient descent and backpropagation to learn features from large datasets effectively."
        sents = (Sentence(text, 0, 0, len(text)),)
        paras.append(Paragraph(
            text=text,
            index=i,
            page_number=1,
            word_count=len(text.split()),
            char_count=len(text),
            is_ocr_derived=False,
            sentences=sents
        ))
    content = DocumentContent("\n".join(p.text for p in paras), tuple(paras), sum(p.word_count for p in paras), len(paras), len(paras))
    source = DocumentSource(f"{prefix}.txt", f"{prefix}.txt", ".txt", 1000, 0.0)
    info = ExtractionInfo(ExtractionMethod.DIGITAL_TEXT, 1, 0, 0.1, ())
    return Document(source, content, info)

def benchmark():
    engine = EmbeddingEngine()
    
    t0 = time.perf_counter()
    engine._ensure_model_loaded()
    t1 = time.perf_counter()
    print(f"Model Load Time: {t1 - t0:.4f}s")

    for size in (20, 100, 300):
        doc_a = make_dummy_doc(size, "DocA")
        doc_b = make_dummy_doc(size, "DocB")
        
        config = EngineConfig(max_paragraphs=300, batch_size=64)
        
        t0 = time.perf_counter()
        res = engine.compare(doc_a, doc_b, config)
        t1 = time.perf_counter()
        print(f"Comparison size {size} paras (Total {size*2} paras): {t1 - t0:.4f}s")

if __name__ == "__main__":
    benchmark()
