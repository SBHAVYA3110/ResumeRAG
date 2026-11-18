"""
Phase 1 Environment & Configuration Verification Test.
Ensures virtual environment, packages, and settings function properly.
"""

import sys
from backend.app.core.config import get_settings


def test_python_version():
    """Verify that the Python runtime is at least version 3.10."""
    assert sys.version_info >= (3, 10), "Python 3.10+ is required."


def test_core_dependencies_importable():
    """Verify that all core libraries can be imported without errors."""
    import fastapi
    import uvicorn
    import pypdf
    import chromadb
    import google.genai
    import pydantic
    import pydantic_settings

    assert fastapi.__name__ == "fastapi"
    assert uvicorn.__name__ == "uvicorn"
    assert pypdf.__name__ == "pypdf"
    assert chromadb.__name__ == "chromadb"
    assert google.genai.__name__ == "google.genai"
    assert pydantic.__name__ == "pydantic"
    assert pydantic_settings.__name__ == "pydantic_settings"


def test_settings_load_properly():
    """Verify that Pydantic settings load configuration values as expected."""
    settings = get_settings()
    assert settings.APP_NAME == "ResumeRAG"
    assert settings.CHROMA_COLLECTION_NAME == "resume_job_docs"
    assert "text-embedding" in settings.EMBEDDING_MODEL
