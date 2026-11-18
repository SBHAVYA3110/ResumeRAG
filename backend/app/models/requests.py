"""
API Request Models.
Defines Pydantic schemas for HTTP request payloads.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload for conversational Q&A endpoint."""
    query: str = Field(..., min_length=2, description="The user's question regarding the uploaded documents")
    document_filter: Optional[str] = Field(
        None,
        description="Optional filename to restrict search to a specific document (e.g. 'my_resume.pdf')",
    )
    n_results: int = Field(4, ge=1, le=10, description="Number of context chunks to retrieve (default: 4)")


class MatchRequest(BaseModel):
    """Payload for comparing a resume with a job description."""
    resume_filename: str = Field(..., min_length=1, description="Filename of the previously uploaded resume")
    job_filename: str = Field(..., min_length=1, description="Filename of the previously uploaded job description")
