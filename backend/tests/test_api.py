"""
HTTP Integration Tests for FastAPI Endpoints (Phase 8).
Simulates real HTTP client requests for document upload, conversational chat,
and resume-job matching using FastAPI's TestClient.
"""

import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

SAMPLE_DIR = Path("data/sample_documents")
RESUME_PATH = SAMPLE_DIR / "sample_resume.pdf"
JD_PATH = SAMPLE_DIR / "sample_job_description.pdf"


# ==============================================================================
# Basic Route & Health Tests
# ==============================================================================

def test_root_endpoint():
    """Verify the root welcome route returns 200 OK and documentation links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "ResumeRAG"
    assert data["status"] == "online"
    assert data["interactive_docs"] == "/docs"


def test_health_check_endpoint():
    """Verify /api/health returns 200 OK and operational status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "ResumeRAG" in data["service"]


def test_frontend_dashboard_endpoint():
    """Verify /app returns 200 OK and serves the compiled React HTML."""
    response = client.get("/app")
    assert response.status_code == 200
    assert "ResumeRAG" in response.text
    assert '<div id="root">' in response.text


# ==============================================================================
# Document Upload Endpoint Tests
# ==============================================================================

def test_upload_non_pdf_rejected():
    """Verify that non-PDF uploads return HTTP 400 Bad Request."""
    file_content = b"Plain text file content, not a PDF."
    response = client.post(
        "/api/documents/upload",
        files={"file": ("invalid_resume.txt", file_content, "text/plain")},
    )
    assert response.status_code == 400
    assert "Only PDF files (.pdf) are supported" in response.json()["detail"]


def test_upload_empty_file_rejected():
    """Verify that uploading an empty 0-byte PDF returns HTTP 400 Bad Request."""
    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "is empty" in response.json()["detail"]


def test_upload_valid_resume_pdf():
    """Verify uploading a valid PDF indexes it in ChromaDB and returns 201 Created."""
    with open(RESUME_PATH, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/documents/upload",
        files={"file": ("sample_resume.pdf", file_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "sample_resume.pdf"
    assert data["total_pages"] == 2
    assert data["total_chunks"] > 0
    assert "Successfully ingested" in data["message"]


def test_upload_valid_job_description_pdf():
    """Verify uploading a job description PDF returns 201 Created."""
    with open(JD_PATH, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/documents/upload",
        files={"file": ("sample_job_description.pdf", file_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "sample_job_description.pdf"
    assert data["total_pages"] == 1
    assert data["total_chunks"] > 0


# ==============================================================================
# Conversational Q&A (Chat) Endpoint Tests
# ==============================================================================

def test_chat_endpoint_grounded_answer():
    """Verify /api/chat returns an answer with citations for an indexed document."""
    payload = {
        "query": "Where does Alex Morgan currently work as Staff AI Engineer?",
        "document_filter": "sample_resume.pdf",
        "n_results": 4,
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["is_grounded"] is True
    assert len(data["citations"]) > 0
    assert "sample_resume.pdf" in data["citations"][0]
    assert len(data["supporting_sources"]) > 0


def test_chat_endpoint_unanswerable_query():
    """Verify /api/chat returns is_grounded=False when asked an unrelated question."""
    payload = {
        "query": "What is the candidate's secret pet name and favorite color?",
        "document_filter": "sample_resume.pdf",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["is_grounded"] is False
    assert "does not contain" in data["answer"].lower()
    assert len(data["citations"]) == 0


# ==============================================================================
# Resume vs. Job Match Endpoint Tests
# ==============================================================================

def test_match_endpoint():
    """Verify /api/match compares resume with job description and returns full report."""
    payload = {
        "resume_filename": "sample_resume.pdf",
        "job_filename": "sample_job_description.pdf",
    }
    response = client.post("/api/match", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert 60 <= data["match_score"] <= 100
    assert data["candidate_name"] == "Alex Morgan"
    assert len(data["matching_skills"]) > 0
    assert any("Python" in s for s in data["matching_skills"])
    assert any("FastAPI" in s for s in data["matching_skills"])
    assert len(data["recommendations"]) >= 2


def test_match_missing_document_returns_404():
    """Verify /api/match returns 404 Not Found if either document has not been uploaded."""
    payload = {
        "resume_filename": "sample_resume.pdf",
        "job_filename": "non_existent_job_description.pdf",
    }
    response = client.post("/api/match", json=payload)
    assert response.status_code == 404
    assert "No indexed content found" in response.json()["detail"]


# ==============================================================================
# Document Deletion Endpoint Tests
# ==============================================================================

def test_delete_document_endpoint():
    """Verify DELETE /api/documents/{filename} returns 200 OK."""
    response = client.delete("/api/documents/sample_resume.pdf")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "sample_resume.pdf" in data["message"]
