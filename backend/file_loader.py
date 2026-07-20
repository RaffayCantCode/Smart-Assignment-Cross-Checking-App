"""
backend/file_loader.py

Handles loading and extracting text from supported document formats.
Currently supports: .pdf, .docx
Future support planned: OCR for scanned PDFs/images
"""

import os
from .utils import UnsupportedFileTypeError, FileProcessingError

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import docx
except ImportError:
    docx = None


def extract_text_from_file(file_path: str) -> str:
    """
    Validates file extension and extracts text.
    Raises UnsupportedFileTypeError or FileProcessingError.
    """
    if not os.path.exists(file_path):
        raise FileProcessingError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return _extract_from_pdf(file_path)
    elif ext == ".docx":
        return _extract_from_docx(file_path)
    else:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{ext}'. Please upload a .pdf or .docx file."
        )


def _extract_from_pdf(file_path: str) -> str:
    if fitz is None:
        raise FileProcessingError("PyMuPDF (fitz) is not installed. Cannot read PDF.")
    
    try:
        doc = fitz.open(file_path)
        text_parts = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_parts.append(page.get_text("text"))
        
        # Placeholder for future OCR integration:
        # if not text_parts or sum(len(p.strip()) for p in text_parts) < 50:
        #     return _perform_ocr(file_path)

        return "\n".join(text_parts)
    except Exception as e:
        raise FileProcessingError(f"Error reading PDF {file_path}: {e}")


def _extract_from_docx(file_path: str) -> str:
    if docx is None:
        raise FileProcessingError("python-docx is not installed. Cannot read DOCX.")
    
    try:
        doc = docx.Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        raise FileProcessingError(f"Error reading DOCX {file_path}: {e}")


def _perform_ocr(file_path: str) -> str:
    """
    Placeholder for future OCR processing module.
    """
    raise NotImplementedError("OCR processing is not yet implemented.")

