"""
Unit Tests for PDF Extraction Service (Phase 2).
Tests clean text extraction, multi-page parsing, in-memory stream processing, and error handling.
"""

import io
from pathlib import Path
import pytest

from backend.app.models.document import (
    EmptyPDFError,
    EncryptedPDFError,
    ExtractedDocument,
    PDFExtractionError,
)
from backend.app.services.pdf_service import clean_extracted_text, extract_text_from_pdf

SAMPLE_DIR = Path("data/sample_documents")
RESUME_PATH = SAMPLE_DIR / "sample_resume.pdf"
JD_PATH = SAMPLE_DIR / "sample_job_description.pdf"


# ==============================================================================
# Text Cleaning Tests
# ==============================================================================

def test_clean_extracted_text():
    """Verify that excessive blank lines, whitespace, and control chars are cleaned."""
    dirty_text = "  Line 1   \r\n\r\n\r\n\r\n   Line 2\x00\x05  \n\n\nLine 3   "
    cleaned = clean_extracted_text(dirty_text)

    # Should collapse multiple newlines to double newlines and strip lines
    assert "Line 1\n\nLine 2\n\nLine 3" == cleaned
    assert "\x00" not in cleaned
    assert "\r" not in cleaned


def test_clean_extracted_text_empty():
    """Verify that empty or None inputs return an empty string safely."""
    assert clean_extracted_text("") == ""
    assert clean_extracted_text(None) == ""


# ==============================================================================
# PDF File Extraction Tests
# ==============================================================================

def test_extract_sample_resume():
    """Verify multi-page extraction from sample_resume.pdf."""
    assert RESUME_PATH.exists(), f"Missing test file at {RESUME_PATH}"

    doc: ExtractedDocument = extract_text_from_pdf(RESUME_PATH)

    assert doc.filename == "sample_resume.pdf"
    assert doc.total_pages == 2
    assert len(doc.pages) == 2

    # Page 1 checks
    page_1 = doc.pages[0]
    assert page_1.page_number == 1
    assert "ALEX MORGAN" in page_1.text
    assert "FastAPI" in page_1.text
    assert "ChromaDB" in page_1.text
    assert page_1.char_count == len(page_1.text)

    # Page 2 checks
    page_2 = doc.pages[1]
    assert page_2.page_number == 2
    assert "FinTech Labs" in page_2.text
    assert "EDUCATION" in page_2.text
    assert "Berkeley" in page_2.text

    # Convenience full_text property
    assert "ALEX MORGAN" in doc.full_text
    assert "Berkeley" in doc.full_text


def test_extract_sample_job_description():
    """Verify single-page extraction from sample_job_description.pdf."""
    assert JD_PATH.exists(), f"Missing test file at {JD_PATH}"

    doc: ExtractedDocument = extract_text_from_pdf(JD_PATH)

    assert doc.filename == "sample_job_description.pdf"
    assert doc.total_pages == 1
    assert doc.pages[0].page_number == 1
    assert "LEAD AI & BACKEND DEVELOPER" in doc.pages[0].text
    assert "REQUIRED QUALIFICATIONS" in doc.pages[0].text
    assert "PostgreSQL" in doc.pages[0].text


# ==============================================================================
# In-Memory Bytes Stream Test (Simulates FastAPI Uploads)
# ==============================================================================

def test_extract_from_in_memory_bytes():
    """Verify extraction when input is raw bytes or an in-memory BytesIO stream."""
    with open(RESUME_PATH, "rb") as f:
        file_bytes = f.read()

    # Test passing raw bytes
    doc_bytes = extract_text_from_pdf(file_bytes, filename="uploaded_resume.pdf")
    assert doc_bytes.filename == "uploaded_resume.pdf"
    assert doc_bytes.total_pages == 2
    assert "ALEX MORGAN" in doc_bytes.pages[0].text

    # Test passing io.BytesIO stream
    stream = io.BytesIO(file_bytes)
    doc_stream = extract_text_from_pdf(stream, filename="stream_resume.pdf")
    assert doc_stream.total_pages == 2
    assert "ALEX MORGAN" in doc_stream.pages[0].text


# ==============================================================================
# Error Handling & Edge Case Tests
# ==============================================================================

def test_extract_file_not_found():
    """Verify FileNotFoundError is raised when a non-existent path is provided."""
    with pytest.raises(FileNotFoundError):
        extract_text_from_pdf("data/sample_documents/non_existent.pdf")


def test_extract_corrupted_file():
    """Verify PDFExtractionError is raised for corrupted or non-PDF bytes."""
    corrupted_data = b"This is definitely not a PDF file header."
    with pytest.raises(PDFExtractionError):
        extract_text_from_pdf(corrupted_data, filename="bad.pdf")


def test_empty_content_raises_empty_pdf_error():
    """Verify EmptyPDFError is raised when a PDF contains no text."""
    # A valid PDF structure that has no text in its stream
    minimal_empty_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n185\n%%EOF\n"
    )
    with pytest.raises(EmptyPDFError):
        extract_text_from_pdf(minimal_empty_pdf, filename="empty.pdf")
