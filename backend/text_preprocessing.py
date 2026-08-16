"""
backend/text_preprocessing.py

Cleans and tokenizes extracted text.
"""

import os
import re
import sys

try:
    import nltk
    # Dynamically register bundled and local nltk_data search paths
    base_dirs = [
        getattr(sys, '_MEIPASS', ''),
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '_internal')),
    ]
    for b in base_dirs:
        if b:
            p = os.path.join(b, 'nltk_data')
            if os.path.isdir(p) and p not in nltk.data.path:
                nltk.data.path.insert(0, p)
except ImportError:
    nltk = None


def remove_quotations(text: str) -> str:
    """Removes text inside double and single quotes."""
    if not text:
        return text
    text = re.sub(r'["“«][^"”»]*["”»]', ' ', text)
    text = re.sub(r"(?<=[\s([(])['‘][^'’]+['’](?=[\s.,!?;:)]|$)", ' ', text)
    return text

def remove_references(text: str) -> str:
    """Removes in-text citation markers like [1], [1-5], (Smith et al., 2020)."""
    if not text:
        return text
    text = re.sub(r'\[\s*\d+(?:\s*[\-,;]\s*\d+)*\s*\]', ' ', text)
    text = re.sub(r'\(\s*[A-Z][a-zA-Z\s.,&]+,?\s*\d{4}\s*(?:,\s*p{1,2}\.?\s*\d+)?\s*\)', ' ', text)
    return text

def remove_bibliography(text: str) -> str:
    """Strips trailing Bibliography / References / Works Cited section."""
    if not text:
        return text
    pattern = re.compile(
        r'\n\s*(?:references|bibliography|works\s+cited|references\s+cited)\s*\n',
        re.IGNORECASE
    )
    match = pattern.search(text)
    if match:
        return text[:match.start()].strip()
    return text

def normalize_formatting(text: str) -> str:
    """Normalizes formatting by lowercasing and stripping non-essential punctuation."""
    if not text:
        return text
    text = text.lower()
    text = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    text = text.replace('—', '-').replace('–', '-')
    text = re.sub(r'[^\w\s.,!?]', ' ', text)
    return text

def clean_text(
    text: str,
    ignore_quotations: bool = False,
    ignore_references: bool = False,
    ignore_bibliography: bool = False,
    ignore_formatting: bool = False,
) -> str:
    """
    Removes excessive whitespace, normalizes newlines, strips padding,
    and applies optional analysis filter options.
    """
    if not text:
        return ""

    if ignore_bibliography:
        text = remove_bibliography(text)

    if ignore_quotations:
        text = remove_quotations(text)

    if ignore_references:
        text = remove_references(text)

    if ignore_formatting:
        text = normalize_formatting(text)

    # Replace multiple spaces/tabs with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Replace 3 or more newlines with exactly two (paragraph break)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def extract_paragraphs(text: str) -> list[str]:
    """
    Splits text into paragraphs based on double newlines.
    Filters out empty or extremely short paragraphs.
    """
    raw_paragraphs = text.split('\n\n')
    
    # Filter out very short lines (like page numbers or single words)
    paragraphs = []
    for p in raw_paragraphs:
        cleaned_p = p.strip()
        # Consider a paragraph valid if it has at least 3 words and 15 characters
        if len(cleaned_p) > 15 and len(cleaned_p.split()) > 2:
            # remove single newlines inside a paragraph (make it a continuous string)
            cleaned_p = re.sub(r'\n', ' ', cleaned_p)
            paragraphs.append(cleaned_p)
            
    return paragraphs


def tokenize_sentences(text: str) -> list[str]:
    """
    Tokenizes text into individual sentences using NLTK if available.
    Falls back gracefully to a robust regex-based splitter if NLTK data is not available.
    """
    if not text:
        return []

    if nltk:
        try:
            return nltk.tokenize.sent_tokenize(text)
        except Exception:
            try:
                nltk.download('punkt_tab', quiet=True)
                nltk.download('punkt', quiet=True)
                return nltk.tokenize.sent_tokenize(text)
            except Exception:
                pass

    # High-accuracy regex sentence splitter that splits on sentence end punctuation followed by spaces
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if not sentences or (len(sentences) == 1 and len(text) > 200 and '\n' in text):
        sentences = [line.strip() for line in text.splitlines() if line.strip()]
    return [s.strip() for s in sentences if s.strip()]


def fix_ocr_artifacts(text: str) -> str:
    """
    Fixes common OCR mistakes.
    """
    if not text:
        return text
    # Fix hyphenation at line breaks
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    # Replace 'l' with '1' in digit contexts (e.g., 'l23' -> '123')
    text = re.sub(r'\bl(?=\d)', '1', text)
    text = re.sub(r'(?<=\d)l\b', '1', text)
    return text

