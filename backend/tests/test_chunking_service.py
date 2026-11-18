"""
Unit Tests for Text Chunking Service (Phase 3).
Verifies chunk size, overlap, boundary preservation, and metadata tracking.
"""

from pathlib import Path
import pytest

from backend.app.models.chunk import ChunkedDocument, TextChunk
from backend.app.models.document import ExtractedDocument
from backend.app.services.chunking_service import (
    chunk_document,
    chunk_page,
    recursive_split_text,
)
from backend.app.services.pdf_service import extract_text_from_pdf

SAMPLE_DIR = Path("data/sample_documents")
RESUME_PATH = SAMPLE_DIR / "sample_resume.pdf"
JD_PATH = SAMPLE_DIR / "sample_job_description.pdf"


# ==============================================================================
# Recursive Split Text Unit Tests
# ==============================================================================

def test_recursive_split_small_input():
    """Verify that text smaller than chunk_size returns a single chunk."""
    text = "Short text that easily fits in one chunk."
    chunks = recursive_split_text(text, chunk_size=500, chunk_overlap=100)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_recursive_split_empty_input():
    """Verify that empty or whitespace-only text returns an empty list."""
    assert recursive_split_text("", chunk_size=500, chunk_overlap=100) == []
    assert recursive_split_text("   \n\n  ", chunk_size=500, chunk_overlap=100) == []


def test_recursive_split_invalid_parameters():
    """Verify ValueError is raised for invalid chunk_size or chunk_overlap."""
    # chunk_overlap >= chunk_size
    with pytest.raises(ValueError, match="strictly less"):
        recursive_split_text("Some text", chunk_size=100, chunk_overlap=100)

    # chunk_overlap > chunk_size
    with pytest.raises(ValueError, match="strictly less"):
        recursive_split_text("Some text", chunk_size=100, chunk_overlap=150)

    # chunk_size <= 0
    with pytest.raises(ValueError, match="greater than 0"):
        recursive_split_text("Some text", chunk_size=0, chunk_overlap=0)

    # negative overlap
    with pytest.raises(ValueError, match="negative"):
        recursive_split_text("Some text", chunk_size=100, chunk_overlap=-10)


def test_recursive_split_overlap_continuity():
    """Verify that adjacent chunks share overlapping text context."""
    paragraphs = [
        "Paragraph One introduces the software architecture and the overall goals of the project.",
        "Paragraph Two elaborates on the database models, indexing strategy, and query performance.",
        "Paragraph Three discusses deployment using Docker containers and Kubernetes clusters.",
    ]
    full_text = "\n\n".join(paragraphs)

    # Small chunk_size to force multiple chunks with overlap
    chunks = recursive_split_text(full_text, chunk_size=150, chunk_overlap=50)

    assert len(chunks) >= 2
    # Verify that consecutive chunks share text
    for i in range(len(chunks) - 1):
        chunk_a = chunks[i]
        chunk_b = chunks[i + 1]
        # At least some trailing words of chunk_a should appear in chunk_b
        trailing_words = chunk_a.split()[-3:]
        trailing_phrase = " ".join(trailing_words)
        assert any(word in chunk_b for word in trailing_words), (
            f"Expected overlap between '{chunk_a}' and '{chunk_b}'"
        )


def test_recursive_split_respects_natural_boundaries():
    """Verify that the splitter prefers paragraph breaks over breaking sentences."""
    p1 = "Paragraph 1: Bullet point detailing Python and FastAPI experience."
    p2 = "Paragraph 2: Bullet point detailing ChromaDB and vector retrieval."
    combined = f"{p1}\n\n{p2}"

    # Target chunk_size large enough for one paragraph but not both
    chunks = recursive_split_text(combined, chunk_size=len(p1) + 10, chunk_overlap=20)

    assert len(chunks) == 2
    assert chunks[0] == p1
    assert chunks[1] == p2


# ==============================================================================
# Document & Page Chunking Integration Tests
# ==============================================================================

def test_chunk_sample_resume():
    """Verify end-to-end chunking on sample_resume.pdf with metadata tracking."""
    doc: ExtractedDocument = extract_text_from_pdf(RESUME_PATH)
    chunked: ChunkedDocument = chunk_document(doc, chunk_size=400, chunk_overlap=80)

    assert chunked.filename == "sample_resume.pdf"
    assert chunked.total_chunks > 0
    assert len(chunked.chunks) == chunked.total_chunks

    # Verify metadata on all chunks
    seen_pages = set()
    for chunk in chunked.chunks:
        assert chunk.source_doc == "sample_resume.pdf"
        assert chunk.page_number in (1, 2)
        seen_pages.add(chunk.page_number)
        assert chunk.char_count == len(chunk.text)
        assert chunk.chunk_id.startswith("sample_resume.pdf_p")

        # ChromaDB metadata dictionary test
        meta = chunk.metadata
        assert meta["source"] == "sample_resume.pdf"
        assert meta["page_number"] in (1, 2)
        assert "chunk_id" in meta

    # Both page 1 and page 2 must be represented
    assert seen_pages == {1, 2}


def test_chunk_sample_job_description():
    """Verify end-to-end chunking on sample_job_description.pdf."""
    doc: ExtractedDocument = extract_text_from_pdf(JD_PATH)
    chunked: ChunkedDocument = chunk_document(doc, chunk_size=400, chunk_overlap=80)

    assert chunked.filename == "sample_job_description.pdf"
    assert chunked.total_chunks > 0

    for chunk in chunked.chunks:
        assert chunk.source_doc == "sample_job_description.pdf"
        assert chunk.page_number == 1
        assert chunk.chunk_id.startswith("sample_job_description.pdf_p1_c")
