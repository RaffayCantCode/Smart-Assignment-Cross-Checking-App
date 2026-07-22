import os
import time
from typing import Optional
import concurrent.futures

from .base import TextExtractor, ProgressCallback
from .ocr import TesseractProvider, EasyOCRProvider, OCRProvider
from ..domain.document import (
    Document, DocumentSource, DocumentContent, ExtractionInfo,
    ExtractionMethod, Paragraph, Sentence, ExtractionWarning
)
from ..text_preprocessing import clean_text, extract_paragraphs, tokenize_sentences, fix_ocr_artifacts
from ..utils import FileProcessingError

try:
    import fitz
except ImportError:
    fitz = None

class PDFExtractor(TextExtractor):
    def __init__(self):
        self._ocr_providers: list[OCRProvider] = [TesseractProvider(), EasyOCRProvider()]

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return ('.pdf',)

    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith(self.supported_extensions)

    def _get_ocr_provider(self) -> Optional[OCRProvider]:
        for provider in self._ocr_providers:
            if provider.is_available():
                return provider
        return None

    def _perform_ocr_on_pages(self, doc, pages_need_ocr: list[int], provider: OCRProvider, progress_callback: Optional[ProgressCallback] = None) -> tuple[list[tuple[int, str]], list[ExtractionWarning]]:
        results = []
        warnings = []
        total = len(pages_need_ocr)
        
        def process_page(page_num):
            try:
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")
                text = provider.extract_text_from_image_bytes(img_bytes, dpi=144)
                if not text.strip():
                    return page_num, "", ExtractionWarning("OCR_PAGE_FAILED", f"OCR failed or returned empty text on page {page_num + 1}", page_num + 1)
                return page_num, text, None
            except Exception as e:
                return page_num, "", ExtractionWarning("OCR_PAGE_FAILED", f"OCR error on page {page_num + 1}: {e}", page_num + 1)

        if total <= 5:
            for i, p in enumerate(pages_need_ocr):
                if progress_callback: progress_callback(20 + int(15 * i / total), f"Reading documents (OCR: page {i+1} of {total})")
                num, txt, warn = process_page(p)
                results.append((num, txt))
                if warn: warnings.append(warn)
        else:
            max_workers = min(os.cpu_count() or 4, total, 4)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(process_page, p): p for p in pages_need_ocr}
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    if progress_callback: progress_callback(20 + int(15 * i / total), f"Reading documents (OCR: page {i+1} of {total})")
                    num, txt, warn = future.result()
                    results.append((num, txt))
                    if warn: warnings.append(warn)
                    
        return results, warnings

    def extract(
        self,
        file_path: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Document:
        if fitz is None:
            raise FileProcessingError("PyMuPDF (fitz) is not installed. Cannot read PDF.")

        start_time = time.time()
        
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise FileProcessingError(f"Error opening PDF {file_path}: {e}")

        pages_text = []
        pages_need_ocr = []
        total_pages = len(doc)
        
        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            page_text = page.get_text("text")
            chars_per_page = len([c for c in page_text if c.strip() and c.isalnum()])
            
            if chars_per_page >= 50:
                pages_text.append((page_num, page_text, False))
            else:
                pages_need_ocr.append(page_num)

        warnings = []
        if pages_need_ocr:
            ocr_provider = self._get_ocr_provider()
            if not ocr_provider:
                warnings.append(ExtractionWarning("OCR_UNAVAILABLE", "OCR is needed for some pages but no OCR engine is available.", 0))
                for p in pages_need_ocr:
                    pages_text.append((p, "", False))
            else:
                ocr_results, ocr_warnings = self._perform_ocr_on_pages(doc, pages_need_ocr, ocr_provider, progress_callback)
                warnings.extend(ocr_warnings)
                for page_num, text in ocr_results:
                    pages_text.append((page_num, text, True))

        doc.close()
        
        pages_text.sort(key=lambda x: x[0])
        
        paragraphs = []
        total_words = 0
        raw_text_parts = []
        
        para_index = 0
        for page_num, text, is_ocr in pages_text:
            raw_text_parts.append(text)
            clean_txt = clean_text(text)
            if is_ocr:
                clean_txt = fix_ocr_artifacts(clean_txt)
                
            para_texts = extract_paragraphs(clean_txt)
            for pt in para_texts:
                sents = tokenize_sentences(pt)
                sentences = []
                char_offset = 0
                for j, s in enumerate(sents):
                    idx = pt.find(s, char_offset)
                    if idx == -1: idx = char_offset
                    sentences.append(Sentence(s, j, idx, idx + len(s)))
                    char_offset = idx + len(s)
                
                p_words = len(pt.split())
                total_words += p_words
                paragraphs.append(Paragraph(
                    text=pt,
                    index=para_index,
                    page_number=page_num + 1,
                    word_count=p_words,
                    char_count=len(pt),
                    is_ocr_derived=is_ocr,
                    sentences=tuple(sentences)
                ))
                para_index += 1

        raw_text = "\n".join(raw_text_parts)

        content = DocumentContent(
            raw_text=raw_text,
            paragraphs=tuple(paragraphs),
            word_count=total_words,
            paragraph_count=len(paragraphs),
            sentence_count=sum(p.sentence_count for p in paragraphs)
        )

        source = DocumentSource(
            file_path=file_path,
            file_name=os.path.basename(file_path),
            extension=".pdf",
            file_size_bytes=os.path.getsize(file_path),
            mtime=os.path.getmtime(file_path)
        )

        ocr_page_count = len(pages_need_ocr)
        if ocr_page_count == 0:
            method = ExtractionMethod.DIGITAL_TEXT
        elif ocr_page_count == total_pages:
            method = ExtractionMethod.OCR
        else:
            method = ExtractionMethod.OCR_HYBRID

        extraction_info = ExtractionInfo(
            method=method,
            page_count=total_pages,
            ocr_page_count=ocr_page_count,
            extraction_time_s=time.time() - start_time,
            warnings=tuple(warnings)
        )

        return Document(source=source, content=content, extraction_info=extraction_info)
