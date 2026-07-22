"""
backend/utils.py

Helper functions and custom exceptions for the backend engine.
"""

class AssignmentAnalyzerError(Exception):
    """Base class for exceptions in this module."""
    pass

class UnsupportedFileTypeError(AssignmentAnalyzerError):
    """Raised when an uploaded file is not a supported format."""
    pass

class FileProcessingError(AssignmentAnalyzerError):
    """Raised when a file cannot be read or processed correctly."""
    pass

class OCRUnavailableError(AssignmentAnalyzerError):
    """Raised when no OCR engine is available."""
    pass

class OCRPageFailedWarning(AssignmentAnalyzerError):
    """Non-fatal: OCR failed on one or more pages but not all."""
    pass

class EngineNotFoundError(AssignmentAnalyzerError):
    """Raised when a requested engine is not registered."""
    pass

class EngineUnavailableError(AssignmentAnalyzerError):
    """Raised when an engine is registered but dependencies are missing."""
    pass

