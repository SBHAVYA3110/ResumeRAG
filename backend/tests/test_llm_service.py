"""
Unit Tests for LLM Generation Service (Phase 6).
Tests grounded Q&A generation, citation extraction, hallucination prevention,
and structured skill match reporting.
"""

from pathlib import Path
import pytest

from backend.app.models.chunk import SearchResult
from backend.app.models.llm import AnswerWithCitations, SkillMatchReport
from backend.app.services.chunking_service import chunk_document
from backend.app.services.llm_service import LLMService, get_llm_service
from backend.app.services.pdf_service import extract_text_from_pdf

SAMPLE_DIR = Path("data/sample_documents")
RESUME_PATH = SAMPLE_DIR / "sample_resume.pdf"
JD_PATH = SAMPLE_DIR / "sample_job_description.pdf"


@pytest.fixture
def llm_service() -> LLMService:
    """Provides an instance of LLMService for testing."""
    return get_llm_service()


@pytest.fixture
def sample_resume_search_results() -> list[SearchResult]:
    """Generates real SearchResult objects from sample_resume.pdf."""
    doc = extract_text_from_pdf(RESUME_PATH)
    chunked = chunk_document(doc, chunk_size=400, chunk_overlap=80)
    return [
        SearchResult(
            chunk_id=c.chunk_id,
            text=c.text,
            source_doc=c.source_doc,
            page_number=c.page_number,
            chunk_index=c.chunk_index,
            distance=0.1,
            similarity_score=0.9,
        )
        for c in chunked.chunks
    ]


@pytest.fixture
def sample_jd_search_results() -> list[SearchResult]:
    """Generates real SearchResult objects from sample_job_description.pdf."""
    doc = extract_text_from_pdf(JD_PATH)
    chunked = chunk_document(doc, chunk_size=400, chunk_overlap=80)
    return [
        SearchResult(
            chunk_id=c.chunk_id,
            text=c.text,
            source_doc=c.source_doc,
            page_number=c.page_number,
            chunk_index=c.chunk_index,
            distance=0.1,
            similarity_score=0.9,
        )
        for c in chunked.chunks
    ]


# ==============================================================================
# Grounded Q&A Tests
# ==============================================================================

def test_grounded_answer_with_valid_citations(
    llm_service: LLMService,
    sample_resume_search_results: list[SearchResult],
):
    """Verify that an answer is generated with exact page and document citations."""
    query = "What backend frameworks and programming languages does the candidate know?"
    ans: AnswerWithCitations = llm_service.generate_grounded_answer(
        query=query,
        context_chunks=sample_resume_search_results,
    )

    assert ans.is_grounded is True
    assert len(ans.citations) > 0
    assert "sample_resume.pdf" in ans.citations[0]
    assert "Page 1" in ans.citations[0]
    assert any(term in ans.answer for term in ("Python", "FastAPI"))


def test_grounded_answer_unanswerable_query(
    llm_service: LLMService,
    sample_resume_search_results: list[SearchResult],
):
    """
    Hallucination Prevention Test:
    When asked a question whose answer is NOT in the document,
    the model must state that the information is missing rather than guessing.
    """
    unrelated_query = "What is the candidate's favorite color and secret pet name?"
    ans: AnswerWithCitations = llm_service.generate_grounded_answer(
        query=unrelated_query,
        context_chunks=sample_resume_search_results,
    )

    assert ans.is_grounded is False
    assert "does not contain" in ans.answer.lower()
    assert len(ans.citations) == 0


def test_grounded_answer_empty_context(llm_service: LLMService):
    """Verify clean handling when no context chunks are supplied."""
    ans = llm_service.generate_grounded_answer(
        query="Any question",
        context_chunks=[],
    )
    assert ans.is_grounded is False
    assert "No relevant document sections" in ans.answer
    assert ans.citations == []


# ==============================================================================
# Skill Match & Gap Analysis Tests
# ==============================================================================

def test_generate_match_report(
    llm_service: LLMService,
    sample_resume_search_results: list[SearchResult],
    sample_jd_search_results: list[SearchResult],
):
    """
    Comprehensive skill matching test:
    Compares real resume chunks with job description chunks and verifies
    score, matching skills, missing skills, and recommendations.
    """
    report: SkillMatchReport = llm_service.generate_match_report(
        resume_chunks=sample_resume_search_results,
        job_chunks=sample_jd_search_results,
    )

    # Alex has 6+ years in Python, FastAPI, ChromaDB, PostgreSQL (strong fit!)
    assert 60 <= report.match_score <= 100
    assert report.candidate_name == "Alex Morgan"
    assert "Lead AI" in report.role_title or "Technical" in report.role_title
    assert len(report.summary) > 20

    # Verify matching skills
    assert any("Python" in s for s in report.matching_skills)
    assert any("FastAPI" in s for s in report.matching_skills)
    assert any("ChromaDB" in s for s in report.matching_skills)

    # Verify recommendations exist
    assert len(report.recommendations) >= 2
