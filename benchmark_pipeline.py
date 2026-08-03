import time
import os
import tempfile
from typing import Dict

from backend.extraction import DocumentLoader
from backend.extraction.pdf_extractor import PDFExtractor
from backend.extraction.docx_extractor import DocxExtractor
from backend.text_preprocessing import clean_text, extract_paragraphs, tokenize_sentences
from backend.engines.embedding_engine import EmbeddingEngine
from backend.engines.base import EngineConfig
from backend.reporting.builder import ReportBuilder
from backend.reporting.exporter import export_report
from test_scanned_docs import create_scanned_pdf

def run_benchmark():
    timings: Dict[str, float] = {}

    # Create test files
    temp_dir = tempfile.gettempdir()
    pdf1_path = os.path.join(temp_dir, "bench_scanned_1.pdf")
    pdf2_path = os.path.join(temp_dir, "bench_scanned_2.pdf")
    
    lines_a = [
        "Smart Assignment Cross Checking System Benchmarking Document One.",
        "Natural language processing uses transformer models for text embeddings.",
        "Sentence embeddings encode semantic meaning into dense vector spaces.",
        "Cosine similarity measures the angle between vector representations."
    ] * 5
    lines_b = [
        "Smart Assignment Cross Checking System Benchmarking Document Two.",
        "Natural language processing uses transformer models for text embeddings.",
        "Machine learning algorithms require high quality feature representations.",
        "Cosine similarity measures the angle between vector representations."
    ] * 5

    create_scanned_pdf(pdf1_path, lines_a)
    create_scanned_pdf(pdf2_path, lines_b)

    loader = DocumentLoader()

    # 1. Document Loading & OCR
    t0 = time.perf_counter()
    doc_a = loader.load(pdf1_path)
    t1 = time.perf_counter()
    timings["Doc 1 Loading & OCR"] = t1 - t0

    t0 = time.perf_counter()
    doc_b = loader.load(pdf2_path)
    t1 = time.perf_counter()
    timings["Doc 2 Loading & OCR"] = t1 - t0

    # Test DOCX loading if available
    docx_path1 = "t1.docx"
    docx_path2 = "t2.docx"
    if os.path.exists(docx_path1) and os.path.exists(docx_path2):
        t0 = time.perf_counter()
        doc_docx1 = loader.load(docx_path1)
        doc_docx2 = loader.load(docx_path2)
        t1 = time.perf_counter()
        timings["DOCX Loading"] = t1 - t0

    # 2. Text Preprocessing
    t0 = time.perf_counter()
    raw_a = doc_a.content.raw_text
    cleaned = clean_text(raw_a)
    paras = extract_paragraphs(cleaned)
    for p in paras:
        _ = tokenize_sentences(p)
    t1 = time.perf_counter()
    timings["Preprocessing"] = t1 - t0

    # 3. Model Loading
    engine = EmbeddingEngine()
    t0 = time.perf_counter()
    engine._ensure_model_loaded()
    t1 = time.perf_counter()
    timings["Embedding Model Load"] = t1 - t0

    # 4. Embedding Generation
    config = EngineConfig()
    texts_a = [p.text for p in doc_a.paragraphs]
    texts_b = [p.text for p in doc_b.paragraphs]

    t0 = time.perf_counter()
    embeds_a = engine._get_embeddings(texts_a, config)
    embeds_b = engine._get_embeddings(texts_b, config)
    t1 = time.perf_counter()
    timings["Embedding Generation"] = t1 - t0

    # 5. Similarity Comparison
    t0 = time.perf_counter()
    result = engine.compare(doc_a, doc_b, config)
    t1 = time.perf_counter()
    timings["Similarity Comparison"] = t1 - t0

    # 6. Report Building
    t0 = time.perf_counter()
    report_model = ReportBuilder.build(result)
    t1 = time.perf_counter()
    timings["Report Building"] = t1 - t0

    # 7. Export Generation
    out_path = os.path.join(temp_dir, "bench_report.html")
    t0 = time.perf_counter()
    export_report(report_model, out_path, "html")
    t1 = time.perf_counter()
    timings["Export Generation"] = t1 - t0

    print("\n" + "="*50)
    print(" TIMING REPORT BENCHMARK (RUN 1 - INITIAL LOAD)")
    print("="*50)
    total = sum(timings.values())
    for stage, sec in timings.items():
        print(f"{stage:<30} ........ {sec:.3f}s")
    print("-" * 50)
    print(f"{'TOTAL':<30} ........ {total:.3f}s")
    print("="*50 + "\n")

    # SECOND RUN (Model already loaded in memory & embedding cache active)
    timings_run2 = {}
    t0 = time.perf_counter()
    doc_a2 = loader.load(pdf1_path)
    doc_b2 = loader.load(pdf2_path)
    t1 = time.perf_counter()
    timings_run2["Document Loading"] = t1 - t0

    t0 = time.perf_counter()
    engine2 = EmbeddingEngine()
    engine2._ensure_model_loaded()
    t1 = time.perf_counter()
    timings_run2["Embedding Model Load"] = t1 - t0

    t0 = time.perf_counter()
    result2 = engine2.compare(doc_a2, doc_b2, config)
    t1 = time.perf_counter()
    timings_run2["Embedding & Comparison (Cached)"] = t1 - t0

    t0 = time.perf_counter()
    report_model2 = ReportBuilder.build(result2)
    t1 = time.perf_counter()
    timings_run2["Report Building"] = t1 - t0

    t0 = time.perf_counter()
    export_report(report_model2, out_path, "html")
    t1 = time.perf_counter()
    timings_run2["Export Generation"] = t1 - t0

    print("="*50)
    print(" TIMING REPORT BENCHMARK (RUN 2 - REUSED MODEL & CACHE)")
    print("="*50)
    total2 = sum(timings_run2.values())
    for stage, sec in timings_run2.items():
        print(f"{stage:<30} ........ {sec:.3f}s")
    print("-" * 50)
    print(f"{'TOTAL RUN 2':<30} ........ {total2:.3f}s")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_benchmark()
