"""
Unit and Integration Tests for Phase 9: PostgreSQL / SQLite Database & History Logging.
Verifies SQLAlchemy ORM models, HistoryService CRUD methods, and database API endpoints.
"""

from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.db_models import ChatMessageRecord, ComparisonRecord, DocumentRecord
from backend.app.models.llm import SkillGapItem, SkillMatchReport
from backend.app.services.history_service import HistoryService


SAMPLE_DIR = Path("data/sample_documents")
RESUME_PATH = SAMPLE_DIR / "sample_resume.pdf"


# ==============================================================================
# In-Memory Database Fixtures for Isolated Testing
# ==============================================================================

@pytest.fixture(name="db_session")
def fixture_db_session():
    """
    Provides an isolated in-memory SQLite database session for testing.
    Uses StaticPool so table schemas persist across all connections.
    """
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(name="client")
def fixture_client(db_session: Session):
    """Overrides the get_db dependency with the isolated test session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# ==============================================================================
# Unit Tests: Document Tracking CRUD
# ==============================================================================

def test_document_record_creation_and_upsert(db_session: Session):
    """Verifies creating a document record and updating it idempotently on re-upload."""
    # 1. Create new record
    doc1 = HistoryService.record_document(
        db=db_session,
        filename="alice_resume.pdf",
        total_pages=2,
        total_chunks=6,
        file_size_bytes=45000,
        doc_type="resume",
    )
    assert doc1.id is not None
    assert doc1.filename == "alice_resume.pdf"
    assert doc1.total_pages == 2
    assert doc1.total_chunks == 6
    assert doc1.doc_type == "resume"

    # 2. Upsert (update existing file with new chunk count)
    doc_updated = HistoryService.record_document(
        db=db_session,
        filename="alice_resume.pdf",
        total_pages=3,
        total_chunks=9,
        file_size_bytes=52000,
        doc_type="resume",
    )
    assert doc_updated.id == doc1.id
    assert doc_updated.total_pages == 3
    assert doc_updated.total_chunks == 9
    assert doc_updated.file_size_bytes == 52000

    # 3. List documents
    docs = HistoryService.list_documents(db_session)
    assert len(docs) == 1
    assert docs[0].filename == "alice_resume.pdf"


def test_document_record_deletion(db_session: Session):
    """Verifies removing a document record upon file deletion."""
    HistoryService.record_document(
        db=db_session,
        filename="temp_job.pdf",
        total_pages=1,
        total_chunks=3,
        file_size_bytes=12000,
        doc_type="job_description",
    )
    assert len(HistoryService.list_documents(db_session)) == 1

    deleted = HistoryService.delete_document_record(db_session, "temp_job.pdf")
    assert deleted is True
    assert len(HistoryService.list_documents(db_session)) == 0

    # Deleting non-existent file returns False safely
    deleted_again = HistoryService.delete_document_record(db_session, "non_existent.pdf")
    assert deleted_again is False


# ==============================================================================
# Unit Tests: Comparison Reports History CRUD
# ==============================================================================

def test_comparison_record_lifecycle(db_session: Session):
    """Verifies persisting comparison reports and decoding JSON columns correctly."""
    sample_report = SkillMatchReport(
        match_score=85,
        summary="Candidate matches core requirements with minor cloud gaps.",
        matching_skills=["Python", "FastAPI", "Docker"],
        missing_skills=["Kubernetes"],
        skill_gaps=[
            SkillGapItem(
                skill="Kubernetes",
                status="Missing",
                recommendation="Deploy small cluster locally using Minikube.",
            )
        ],
        recommendations=["Gain hands-on experience with Kubernetes orchestration."],
        candidate_name="Alex Morgan",
        role_title="Backend Engineer",
    )

    record = HistoryService.record_comparison(
        db=db_session,
        report=sample_report,
        resume_filename="alex_resume.pdf",
        job_filename="backend_jd.pdf",
    )

    assert record.id is not None
    assert record.candidate_name == "Alex Morgan"
    assert record.match_score == 85
    # Test JSON property getters
    assert record.matching_skills == ["Python", "FastAPI", "Docker"]
    assert record.missing_skills == ["Kubernetes"]
    assert record.recommendations == ["Gain hands-on experience with Kubernetes orchestration."]

    # Verify list query
    comparisons = HistoryService.list_comparisons(db_session, limit=10)
    assert len(comparisons) == 1
    assert comparisons[0].resume_filename == "alex_resume.pdf"


# ==============================================================================
# Unit Tests: Chat Message History CRUD
# ==============================================================================

def test_chat_message_record_lifecycle(db_session: Session):
    """Verifies logging chat queries and retrieving conversation history."""
    msg = HistoryService.record_chat_message(
        db=db_session,
        query="What is the candidate's degree?",
        answer="Alex Morgan holds a Bachelor of Science in Computer Science.",
        citations=["alex_resume.pdf (Page 2)"],
        is_grounded=True,
        document_filter="alex_resume.pdf",
    )

    assert msg.id is not None
    assert msg.query == "What is the candidate's degree?"
    assert msg.is_grounded is True
    assert msg.citations == ["alex_resume.pdf (Page 2)"]

    history = HistoryService.list_chat_messages(db_session, limit=5)
    assert len(history) == 1
    assert history[0].answer == "Alex Morgan holds a Bachelor of Science in Computer Science."


# ==============================================================================
# Integration Tests: History REST Endpoints
# ==============================================================================

def test_api_document_tracking_and_listing(client: TestClient):
    """Verifies that uploading a document reflects in GET /api/documents and DELETE /api/documents."""
    # 1. Initially document list is empty in the isolated DB
    resp_init = client.get("/api/documents")
    assert resp_init.status_code == 200
    assert resp_init.json() == []

    # 2. Upload valid PDF
    with open(RESUME_PATH, "rb") as f:
        file_bytes = f.read()

    upload_resp = client.post(
        "/api/documents/upload",
        files={"file": ("history_resume.pdf", file_bytes, "application/pdf")},
    )
    assert upload_resp.status_code == 201

    # 3. GET /api/documents now contains history_resume.pdf
    resp_list = client.get("/api/documents")
    assert resp_list.status_code == 200
    docs = resp_list.json()
    assert len(docs) == 1
    assert docs[0]["filename"] == "history_resume.pdf"
    assert docs[0]["doc_type"] == "resume"

    # 4. DELETE /api/documents removes it
    del_resp = client.delete("/api/documents/history_resume.pdf")
    assert del_resp.status_code == 200

    resp_after = client.get("/api/documents")
    assert resp_after.status_code == 200
    assert len(resp_after.json()) == 0


def test_api_chat_history_logging(client: TestClient):
    """Verifies that asking questions via POST /api/chat records to GET /api/history/chat."""
    # Ingest resume document first
    with open(RESUME_PATH, "rb") as f:
        file_bytes = f.read()

    client.post(
        "/api/documents/upload",
        files={"file": ("history_chat_resume.pdf", file_bytes, "application/pdf")},
    )

    # Perform chat
    chat_resp = client.post(
        "/api/chat",
        json={
            "query": "Where did the candidate work as Staff Engineer?",
            "document_filter": "history_chat_resume.pdf",
            "n_results": 2,
        },
    )
    assert chat_resp.status_code == 200

    # Verify history endpoint
    hist_resp = client.get("/api/history/chat")
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) >= 1
    assert history[0]["query"] == "Where did the candidate work as Staff Engineer?"
    assert len(history[0]["citations"]) > 0

    # Clean up
    client.delete("/api/documents/history_chat_resume.pdf")
