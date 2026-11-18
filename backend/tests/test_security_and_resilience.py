"""
Security, Resilience, and Defensive Boundary Tests for Phase 11.
Verifies directory traversal defense, file size limits, corrupt stream rejection, and secret isolation.
"""

from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from backend.app.api.routes import MAX_FILE_SIZE_BYTES, sanitize_filename
from backend.app.main import app

client = TestClient(app)

SAMPLE_DIR = Path("data/sample_documents")
RESUME_PATH = SAMPLE_DIR / "sample_resume.pdf"


# ==============================================================================
# 1. Path Traversal & Filename Sanitization Tests
# ==============================================================================

def test_sanitize_filename_utility():
    """Verify that sanitize_filename strips directory traversal characters."""
    assert sanitize_filename("../../../../etc/shadow.pdf") == "shadow.pdf"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.pdf") == "cmd.pdf"
    assert sanitize_filename("my resume (1).pdf") == "my_resume__1_.pdf"
    assert sanitize_filename("../../../nested/folder/doc.pdf") == "doc.pdf"
    assert sanitize_filename("") == "document.pdf"


def test_path_traversal_upload_defense():
    """Verify that uploading a file with path traversal in its filename is sanitized."""
    with open(RESUME_PATH, "rb") as f:
        file_bytes = f.read()

    # Attempt to upload with path traversal name
    traversal_filename = "../../../../secret_resume.pdf"
    response = client.post(
        "/api/documents/upload",
        files={"file": (traversal_filename, file_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    # The filename must be sanitized — no '../' or '/'
    assert ".." not in data["filename"]
    assert "/" not in data["filename"]
    assert "\\" not in data["filename"]
    assert data["filename"] == "secret_resume.pdf"

    # Clean up
    client.delete("/api/documents/secret_resume.pdf")


def test_path_traversal_delete_defense():
    """Verify deleting with directory traversal characters is sanitized safely."""
    response = client.delete("/api/documents/..%2F..%2Fetc%2Fpasswd.pdf")
    # Must not throw unhandled 500 error
    assert response.status_code in (200, 400, 404)


# ==============================================================================
# 2. File Size Quota & Denial of Service Defense
# ==============================================================================

def test_payload_exceeding_10mb_rejected():
    """Verify that uploading a file larger than 10 MB is rejected with HTTP 413."""
    oversized_bytes = b"%PDF-1.4 " + b"X" * (MAX_FILE_SIZE_BYTES + 1024)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("huge_document.pdf", oversized_bytes, "application/pdf")},
    )
    assert response.status_code == 413
    assert "exceeds the maximum allowed size" in response.json()["detail"]


# ==============================================================================
# 3. Corrupt & Malformed PDF Handling
# ==============================================================================

def test_corrupt_binary_pdf_rejected():
    """Verify that malformed or non-readable binary streams return HTTP 400."""
    corrupt_bytes = b"%PDF-1.5 \x00\x01\x02\x03\xfe\xff Non-valid corrupt PDF stream"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("corrupt.pdf", corrupt_bytes, "application/pdf")},
    )
    assert response.status_code == 400
    assert "Failed to process PDF" in response.json()["detail"] or "Empty" in response.json()["detail"]


# ==============================================================================
# 4. Secret Isolation & Repository Hygiene Tests
# ==============================================================================

def test_gitignore_protects_secrets_and_artifacts():
    """Verify that .gitignore excludes secrets, database files, and node_modules."""
    gitignore_path = Path(".gitignore")
    assert gitignore_path.exists(), ".gitignore file must exist in repository root."

    content = gitignore_path.read_text(encoding="utf-8")
    assert ".env" in content
    assert ".venv" in content
    assert "node_modules" in content
    assert "*.db" in content or "resumerag.db" in content
    assert "chroma_db" in content


def test_env_example_has_no_hardcoded_secrets():
    """Verify that .env.example contains only template placeholder strings."""
    env_example_path = Path(".env.example")
    assert env_example_path.exists()
    content = env_example_path.read_text(encoding="utf-8")

    # Ensure no real Gemini API key (starts with AIza...) is accidentally present in the template
    assert "AIza" not in content
    assert "your_gemini_api_key_here" in content or "your_" in content


# ==============================================================================
# 5. Containerization & Deployment Configuration Tests
# ==============================================================================

def test_docker_and_deployment_configurations():
    """Verify production Dockerfile, docker-compose, and .dockerignore are properly formed."""
    dockerfile_path = Path("Dockerfile")
    compose_path = Path("docker-compose.yml")
    dockerignore_path = Path(".dockerignore")

    assert dockerfile_path.exists(), "Production Dockerfile must exist."
    assert compose_path.exists(), "docker-compose.yml must exist."
    assert dockerignore_path.exists(), ".dockerignore must exist."

    # Validate multi-stage build structure
    dockerfile_content = dockerfile_path.read_text(encoding="utf-8")
    assert "AS frontend-builder" in dockerfile_content
    assert "AS runner" in dockerfile_content
    assert "HEALTHCHECK" in dockerfile_content

    # Validate docker-compose structure
    compose_content = compose_path.read_text(encoding="utf-8")
    assert "resumerag:" in compose_content
    assert "chroma_data:" in compose_content

    # Validate .dockerignore structure
    dockerignore_content = dockerignore_path.read_text(encoding="utf-8")
    assert ".env" in dockerignore_content
    assert "node_modules" in dockerignore_content
    assert ".venv" in dockerignore_content
