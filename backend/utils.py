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

