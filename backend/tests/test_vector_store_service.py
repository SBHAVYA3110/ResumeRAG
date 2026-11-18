"""
Unit Tests for Vector Store Service (Phase 5).
Tests ChromaDB collection management, embedding storage, similarity search,
metadata filtering, idempotence, and integration with sample documents.
"""

from pathlib import Path
import uuid
import chromadb
import pytest

from backend.app.models.chunk import TextChunk
from backend.app.services.chunking_service import chunk_document
from backend.app.services.embedding_service import get_embedding_service
from backend.app.services.pdf_service import extract_text_from_pdf
from backend.app.services.vector_store_service import VectorStoreService

SAMPLE_DIR = Path("data/sample_documents")
RESUME_PATH = SAMPLE_DIR / "sample_resume.pdf"
JD_PATH = SAMPLE_DIR / "sample_job_description.pdf"


@pytest.fixture
def in_memory_vector_store() -> VectorStoreService:
    """Provides an isolated, in-memory ChromaDB service with a unique collection for each test."""
    client = chromadb.EphemeralClient()
    return VectorStoreService(
        client=client,
        collection_name=f"test_col_{uuid.uuid4().hex[:8]}",
        embedding_service=get_embedding_service(),
    )


# ==============================================================================
# Basic Vector Store Operations
# ==============================================================================

def test_add_and_retrieve_chunks(in_memory_vector_store: VectorStoreService):
    """Verify storing chunks and retrieving the top-ranked match with metadata."""
    chunks = [
        TextChunk(
            chunk_id="resume.pdf_p1_c0",
            text="Alex has 6+ years in Python, FastAPI microservices, and ChromaDB vector search.",
            source_doc="resume.pdf",
            page_number=1,
            chunk_index=0,
            char_count=82,
        ),
        TextChunk(
            chunk_id="resume.pdf_p2_c0",
            text="Education: Bachelor of Science in Computer Science from UC Berkeley.",
            source_doc="resume.pdf",
            page_number=2,
            chunk_index=0,
            char_count=69,
        ),
    ]

    added = in_memory_vector_store.add_chunks(chunks)
    assert added == 2
    assert in_memory_vector_store.count() == 2

    # Query specifically for backend programming skills
    results = in_memory_vector_store.query_similar(
        query_text="FastAPI Python backend microservices",
        n_results=1,
    )

    assert len(results) == 1
    top_match = results[0]
    assert top_match.chunk_id == "resume.pdf_p1_c0"
    assert top_match.page_number == 1
    assert top_match.source_doc == "resume.pdf"
    assert "FastAPI" in top_match.text
    assert top_match.similarity_score > 0.0


def test_metadata_filtering(in_memory_vector_store: VectorStoreService):
    """Verify that 'where' metadata filters isolate results to a specific document."""
    chunks = [
        TextChunk(
            chunk_id="resume_c0",
            text="Candidate has built distributed Python applications.",
            source_doc="resume.pdf",
            page_number=1,
            chunk_index=0,
            char_count=52,
        ),
        TextChunk(
            chunk_id="jd_c0",
            text="Company requires 5+ years building distributed Python applications.",
            source_doc="job_description.pdf",
            page_number=1,
            chunk_index=0,
            char_count=68,
        ),
    ]
    in_memory_vector_store.add_chunks(chunks)

    # Filter to search ONLY within job_description.pdf
    results = in_memory_vector_store.query_similar(
        query_text="distributed Python applications",
        n_results=5,
        where_filter={"source": "job_description.pdf"},
    )

    assert len(results) == 1
    assert results[0].chunk_id == "jd_c0"
    assert results[0].source_doc == "job_description.pdf"


def test_upsert_idempotence(in_memory_vector_store: VectorStoreService):
    """Verify that re-adding the same chunk IDs does not create duplicates."""
    chunk = TextChunk(
        chunk_id="unique_id_1",
        text="Sample text content.",
        source_doc="doc.pdf",
        page_number=1,
        chunk_index=0,
        char_count=20,
    )

    # Add the chunk twice
    in_memory_vector_store.add_chunks([chunk])
    in_memory_vector_store.add_chunks([chunk])

    assert in_memory_vector_store.count() == 1


def test_delete_document(in_memory_vector_store: VectorStoreService):
    """Verify deleting all chunks originating from a specific source document."""
    chunks = [
        TextChunk(
            chunk_id="docA_c0",
            text="Doc A content",
            source_doc="docA.pdf",
            page_number=1,
            chunk_index=0,
            char_count=13,
        ),
        TextChunk(
            chunk_id="docB_c0",
            text="Doc B content",
            source_doc="docB.pdf",
            page_number=1,
            chunk_index=0,
            char_count=13,
        ),
    ]
    in_memory_vector_store.add_chunks(chunks)
    assert in_memory_vector_store.count() == 2

    in_memory_vector_store.delete_document("docA.pdf")
    assert in_memory_vector_store.count() == 1

    # Verify only docB remains
    remaining = in_memory_vector_store.query_similar("content", n_results=5)
    assert len(remaining) == 1
    assert remaining[0].source_doc == "docB.pdf"


def test_empty_collection_query(in_memory_vector_store: VectorStoreService):
    """Verify that querying an empty collection returns an empty list without error."""
    assert in_memory_vector_store.count() == 0
    results = in_memory_vector_store.query_similar("any question", n_results=3)
    assert results == []


# ==============================================================================
# Full Pipeline Integration Test: Real PDFs -> Chunks -> Embeddings -> ChromaDB
# ==============================================================================

def test_full_rag_ingestion_and_retrieval(in_memory_vector_store: VectorStoreService):
    """
    End-to-end integration test spanning Phases 2 through 5:
    1. Parse sample_resume.pdf and sample_job_description.pdf with PyPDF.
    2. Split both into chunks with metadata.
    3. Index all chunks into ChromaDB with 768-dim embeddings.
    4. Execute realistic interview queries and verify accurate retrieval and source attribution.
    """
    # Step 1 & 2: Parse and Chunk
    resume_doc = extract_text_from_pdf(RESUME_PATH)
    jd_doc = extract_text_from_pdf(JD_PATH)

    resume_chunked = chunk_document(resume_doc, chunk_size=400, chunk_overlap=80)
    jd_chunked = chunk_document(jd_doc, chunk_size=400, chunk_overlap=80)

    # Step 3: Index into ChromaDB
    in_memory_vector_store.upsert_document(resume_chunked)
    in_memory_vector_store.upsert_document(jd_chunked)

    total_chunks = resume_chunked.total_chunks + jd_chunked.total_chunks
    assert in_memory_vector_store.count() == total_chunks

    # Query 1: Ask about candidate's AI & Vector Search experience
    query_1 = "Does candidate have experience with ChromaDB or vector search?"
    results_1 = in_memory_vector_store.query_similar(
        query_text=query_1,
        n_results=2,
        where_filter={"source": "sample_resume.pdf"},
    )
    assert len(results_1) > 0
    top_1 = results_1[0]
    assert top_1.source_doc == "sample_resume.pdf"
    assert top_1.page_number in (1, 2)
    assert any(term in top_1.text for term in ("ChromaDB", "RAG", "vector"))

    # Query 2: Ask about the job role's primary responsibilities
    query_2 = "What are the primary key responsibilities and architecture duties?"
    results_2 = in_memory_vector_store.query_similar(
        query_text=query_2,
        n_results=1,
        where_filter={"source": "sample_job_description.pdf"},
    )
    assert len(results_2) == 1
    top_2 = results_2[0]
    assert top_2.source_doc == "sample_job_description.pdf"
    assert any(term in top_2.text for term in ("RESPONSIBILITIES", "architecture", "RAG"))
