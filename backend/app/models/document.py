"""
Document Models and Custom Exceptions.
Defines structured data classes for extracted document content.
"""

from typing import List
from pydantic import BaseModel, Field


# ==============================================================================
# Custom Domain Exceptions
# ==============================================================================

class PDFExtractionError(Exception):
    """Base exception for all PDF extraction failures."""
    pass


class EncryptedPDFError(PDFExtractionError):
    """Raised when a PDF is password-protected and cannot be read."""
    pass


class EmptyPDFError(PDFExtractionError):
    """Raised when a PDF contains zero readable text (e.g. scanned image)."""
    pass


# ==============================================================================
# Pydantic Schemas for Extracted Content
# ==============================================================================

class ExtractedPage(BaseModel):
    """Represents a single page extracted from a document."""
    page_number: int = Field(..., description="1-indexed human-readable page number")
    text: str = Field(..., description="Cleaned text content of the page")
    char_count: int = Field(..., description="Total characters in this page")


class ExtractedDocument(BaseModel):
    """Represents the complete parsed document containing all extracted pages."""
    filename: str = Field(..., description="Original name of the uploaded document")
    total_pages: int = Field(..., description="Total number of pages parsed")
    pages: List[ExtractedPage] = Field(default_factory=list, description="List of parsed pages")

    @property
    def full_text(self) -> str:
        """Convenience property to get all document text joined together."""
        return "\n\n".join(page.text for page in self.pages if page.text.strip())
