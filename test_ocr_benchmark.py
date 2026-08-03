import time
import os
import tempfile
import fitz
from PIL import Image, ImageDraw, ImageFont

from backend.extraction.pdf_extractor import PDFExtractor
from backend.extraction.ocr.tesseract_provider import TesseractProvider
from backend.engines.embedding_engine import EmbeddingEngine
from backend.text_preprocessing import clean_text, extract_paragraphs, tokenize_sentences
from backend.reporting.builder import ReportBuilder
from backend.reporting.exporter import export_report

def draw_text_image(text_lines, width=1000, height=1200):
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except IOError:
        font = ImageFont.load_default()
    
    y = 50
    for line in text_lines:
        draw.text((50, y), line, fill=(0, 0, 0), font=font)
        y += 30
    return img

def create_real_scanned_pdf(file_path, num_pages=5):
    doc = fitz.open()
    for p in range(num_pages):
        lines = [
            f"Page {p+1} Scanned Assignment Document Header Information.",
            "This is paragraph one discussing computer science and machine learning concepts in detail.",
            "Algorithms and data structures form the foundation of efficient software engineering.",
            "Neural networks use backpropagation to optimize gradient descent optimization functions.",
            "Cross checking assignments requires robust natural language processing techniques."
        ]
        img = draw_text_image(lines)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
            tmp_path = tmp_img.name
            img.save(tmp_path, format="PNG")
        
        page = doc.new_page(width=1000, height=1200)
        rect = fitz.Rect(0, 0, 1000, 1200)
        page.insert_image(rect, filename=tmp_path)
        try:
            os.remove(tmp_path)
        except OSError:
            pass
    doc.save(file_path)
    doc.close()

def main():
    temp_dir = tempfile.gettempdir()
    pdf1 = os.path.join(temp_dir, "test_scanned_5p_1.pdf")
    pdf2 = os.path.join(temp_dir, "test_scanned_5p_2.pdf")

    print("Generating 5-page scanned PDFs...")
    create_real_scanned_pdf(pdf1, num_pages=5)
    create_real_scanned_pdf(pdf2, num_pages=5)

    extractor = PDFExtractor()
    
    t0 = time.perf_counter()
    doc1 = extractor.extract(pdf1)
    t1 = time.perf_counter()
    print(f"5-page Scanned PDF 1 Extraction (OCR): {t1 - t0:.3f}s")

    t0 = time.perf_counter()
    doc2 = extractor.extract(pdf2)
    t1 = time.perf_counter()
    print(f"5-page Scanned PDF 2 Extraction (OCR): {t1 - t0:.3f}s")

    # Clean up
    for p in (pdf1, pdf2):
        if os.path.exists(p):
            os.remove(p)

if __name__ == "__main__":
    main()
