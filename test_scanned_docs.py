import os
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont
import fitz

from backend.extraction.ocr.tesseract_provider import TesseractProvider
from backend.extraction.pdf_extractor import PDFExtractor
from backend.assignment_analyzer import AssignmentAnalyzer
from backend.domain.document import ExtractionMethod

def draw_text_image(text_lines, width=800, height=600):
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()
    
    y = 40
    for line in text_lines:
        draw.text((40, y), line, fill=(0, 0, 0), font=font)
        y += 35
    return img

def create_scanned_pdf(file_path, text_lines):
    img = draw_text_image(text_lines)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        tmp_img_path = tmp_img.name
        img.save(tmp_img_path, format="PNG")
        
    doc = fitz.open()
    page = doc.new_page(width=800, height=600)
    rect = fitz.Rect(0, 0, 800, 600)
    page.insert_image(rect, filename=tmp_img_path)
    doc.save(file_path)
    doc.close()
    
    try:
        os.remove(tmp_img_path)
    except OSError:
        pass

def run_tests():
    print("=" * 65)
    print(" SCANNED DOCUMENT (OCR) FUNCTIONALITY TEST SUITE")
    print("=" * 65)
    
    # 1. Test Tesseract Provider
    print("\n[Step 1/4] Checking Tesseract OCR Provider Status...")
    provider = TesseractProvider()
    if provider.is_available():
        print("  [SUCCESS] Tesseract OCR is installed and detected properly!")
    else:
        print("  [WARNING] Tesseract OCR engine was NOT detected on this system.")
        print("  Default locations checked: C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
        print("  To enable OCR on scanned documents, please install Tesseract-OCR.")
    
    # 2. Create synthetic scanned PDF assignments
    print("\n[Step 2/4] Generating synthetic scanned PDF assignments (raster images)...")
    temp_dir = tempfile.gettempdir()
    pdf1_path = os.path.join(temp_dir, "test_scanned_assign_1.pdf")
    pdf2_path = os.path.join(temp_dir, "test_scanned_assign_2.pdf")
    
    doc1_lines = [
        "Smart Assignment Cross Checking System Test Assignment One.",
        "Computer science involves studying algorithms and data structures.",
        "Artificial intelligence enables machines to learn from empirical data.",
        "Software engineering principles guide high quality code creation."
    ]
    
    doc2_lines = [
        "Smart Assignment Cross Checking System Test Assignment Two.",
        "Computer science involves studying algorithms and data structures.",
        "Machine learning models predict patterns based on historical data.",
        "Software engineering principles guide high quality code creation."
    ]
    
    create_scanned_pdf(pdf1_path, doc1_lines)
    create_scanned_pdf(pdf2_path, doc2_lines)
    print(f"  Created sample scanned PDF 1: {pdf1_path}")
    print(f"  Created sample scanned PDF 2: {pdf2_path}")
    
    # 3. Extract text using PDFExtractor
    print("\n[Step 3/4] Extracting text from scanned PDF using PDFExtractor...")
    extractor = PDFExtractor()
    
    def log_progress(pct, msg):
        print(f"    Progress [{pct}%]: {msg}")
        
    doc1 = extractor.extract(pdf1_path, progress_callback=log_progress)
    print(f"  Extraction Method: {doc1.extraction_info.method.value}")
    print(f"  Extracted Paragraphs Count: {len(doc1.paragraphs)}")
    print(f"  Word Count: {doc1.content.word_count}")
    print("  Extracted Text Snippet:")
    print("    " + doc1.content.raw_text.replace("\n", " ")[:150] + "...")
    
    # 4. Run full end-to-end Assignment Analyzer
    print("\n[Step 4/4] Running end-to-end Assignment Analyzer on scanned PDFs...")
    analyzer = AssignmentAnalyzer(progress_callback=log_progress)
    result = analyzer.analyze_one_to_one(pdf1_path, pdf2_path)
    
    print("\n" + "=" * 65)
    print(" TEST RESULTS SUMMARY")
    print("=" * 65)
    print(f"  Analysis Status: {'SUCCESS' if not result.get('error') else 'ERROR'}")
    if result.get('error'):
        print(f"  Error Details: {result.get('error')}")
    else:
        stats = result.get("statistics", {})
        print(f"  Similarity Score: {stats.get('score_percent', 0)}%")
        print(f"  Similarity Band: {stats.get('band', 'N/A')}")
        print(f"  Matched Paragraphs: {len(result.get('matched_paragraphs', []))}")
        print(f"  Summary: {result.get('summary', '')}")
    
    # Clean up test files
    for path in (pdf1_path, pdf2_path):
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

if __name__ == "__main__":
    run_tests()
