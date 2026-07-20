"""
backend/text_preprocessing.py

Cleans and tokenizes extracted text.
"""

import re
try:
    import nltk
    # Ensure punkt is available
    # nltk.download('punkt', quiet=True) # Usually it's better to download once during installation
except ImportError:
    nltk = None


def clean_text(text: str) -> str:
    """
    Removes excessive whitespace, normalizes newlines, and strips padding.
    """
    if not text:
        return ""
    
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
    Falls back to a simple regex splitter if NLTK is missing.
    """
    if not text:
        return []
        
    if nltk:
        try:
            return nltk.tokenize.sent_tokenize(text)
        except LookupError:
            # In case punkt is not downloaded
            nltk.download('punkt', quiet=True)
            nltk.download('punkt_tab', quiet=True)
            return nltk.tokenize.sent_tokenize(text)
            
    # Fallback basic regex splitting if NLTK completely unavailable
    # Splits on . ! ? followed by space and capital letter, or end of string
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z]|$)', text)
    return [s.strip() for s in sentences if s.strip()]

