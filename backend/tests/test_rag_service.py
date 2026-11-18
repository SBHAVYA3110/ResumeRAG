"""
Integration Tests for Unified RAG Pipeline (Phase 7).
Tests end-to-end document ingestion, conversational question answering,
source reference attribution, and resume-job comparison.
"""

from pathlib import Path
import uuid
import chromadb
import pytest

from backend.app.models.llm import SkillMatchReport
from backend.app.models.rag import IngestionResponse, QueryResponse
from backend.app.services.embedding_service import get_embedding_service
from backend.app.services.llm_service import get_llm_service
from backend.app.services.rag_service import RAGPipeline
from backend.app.services.vector_store_service import VectorStoreService

SAMPLE_DIR = Path("data/sample_documents")
RESUME_PATH = SAMPLE_DIR / "sample_resume.pdf"
JD_PATH = SAMPLE_DIR / "sample_job_description.pdf"


@pytest.fixture
def rag_pipeline() -> RAGPipeline:
    """Provides a fresh, isolated RAGPipeline with an in-memory vector store for testing."""
    client = chromadb.EphemeralClient()
    vector_store = VectorStoreService(
        client=client,
        collection_name=f"rag_test_{uuid.uuid4().hex[:8]}",
        embedding_service=get_embedding_service(),
    )
    llm_service = get_llm_service()
    return RAGPipeline(vector_store=vector_store, llm_service=llm_service)


# ==============================================================================
# Ingestion Tests
# ==============================================================================

def test_pipeline_ingest_document(rag_pipeline: RAGPipeline):
    """Verify that the pipeline parses, chunks, and stores a PDF in one call."""
    res: IngestionResponse = rag_pipeline.ingest_document(RESUME_PATH)

    assert res.filename == "sample_resume.pdf"
    assert res.total_pages == 2
    assert res.total_chunks > 0
    assert "Successfully ingested" in res.message
    assert rag_pipeline.vector_store.count() == res.total_chunks


# ==============================================================================
# Q&A with Citations Tests
# ==============================================================================

def test_pipeline_ask_with_citations(rag_pipeline: RAGPipeline):
    """Verify conversational Q&A retrieves relevant context and cites the source page."""
    # Ingest resume
    rag_pipeline.ingest_document(RESUME_PATH)

    query = "Where does Alex Morgan currently work as Staff AI Engineer?"
    res: QueryResponse = rag_pipeline.ask(query, document_filter="sample_resume.pdf")

    assert res.is_grounded is True
    assert len(res.citations) > 0
    assert "sample_resume.pdf" in res.citations[0]
    assert any("CloudScale" in s.text for s in res.supporting_sources)
    assert len(res.supporting_sources) > 0


def test_pipeline_ask_unanswerable_query(rag_pipeline: RAGPipeline):
    """Verify that questions with no grounding in the document return is_grounded=False."""
    rag_pipeline.ingest_document(RESUME_PATH)

    query = "What is the candidate's favorite color and secret pet name?"
    res: QueryResponse = rag_pipeline.ask(query, document_filter="sample_resume.pdf")

    assert res.is_grounded is False
    assert "does not contain" in res.answer.lower()
    assert len(res.citations) == 0


# ==============================================================================
# Multi-Document Comparison Tests
# ==============================================================================

def test_pipeline_compare_resume_and_job(rag_pipeline: RAGPipeline):
    """Verify multi-document comparison produces a comprehensive match report."""
    # Ingest both documents into the pipeline
    rag_pipeline.ingest_document(RESUME_PATH)
    rag_pipeline.ingest_document(JD_PATH)

    report: SkillMatchReport = rag_pipeline.compare_resume_and_job(
        resume_filename="sample_resume.pdf",
        job_filename="sample_job_description.pdf",
    )

    assert 60 <= report.match_score <= 100
    assert report.candidate_name == "Alex Morgan"
    assert "Lead AI" in report.role_title or "Technical" in report.role_title
    assert any("Python" in s for s in report.matching_skills)
    assert any("FastAPI" in s for s in report.matching_skills)
    assert len(report.recommendations) >= 2


def test_pipeline_compare_missing_document_raises_error(rag_pipeline: RAGPipeline):
    """Verify ValueError is raised if attempting to compare an un-ingested document."""
    rag_pipeline.ingest_document(RESUME_PATH)

    with pytest.raises(ValueError, match="No indexed content found for job description"):
        rag_pipeline.compare_resume_and_job(
            resume_filename="sample_resume.pdf",
            job_filename="non_existent_job.pdf",
        )


def test_pipeline_delete_document(rag_pipeline: RAGPipeline):
    """Verify deleting a document from the pipeline purges its chunks."""
    res_resume = rag_pipeline.ingest_document(RESUME_PATH)
    res_jd = rag_pipeline.ingest_document(JD_PATH)
    total_before = res_resume.total_chunks + res_jd.total_chunks
    assert rag_pipeline.vector_store.count() == total_before

    rag_pipeline.delete_document("sample_resume.pdf")
    assert rag_pipeline.vector_store.count() == res_jd.total_chunks
