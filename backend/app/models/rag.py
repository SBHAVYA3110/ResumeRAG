"""
RAG Pipeline Models.
Defines structured responses for document ingestion and conversational Q&A.
"""

from typing import List
from pydantic import BaseModel, Field

from backend.app.models.chunk import SearchResult


class IngestionResponse(BaseModel):
    """Result of parsing, chunking, embedding, and indexing a document."""
    filename: str = Field(..., description="Name of the processed document")
    total_pages: int = Field(..., description="Number of pages extracted from the PDF")
    total_chunks: int = Field(..., description="Number of discrete vector chunks stored in ChromaDB")
    message: str = Field(..., description="Human-readable status summary")


class QueryResponse(BaseModel):
    """Result of querying the RAG pipeline."""
    query: str = Field(..., description="The user's original question")
    answer: str = Field(..., description="The AI answer grounded in the retrieved document context")
    citations: List[str] = Field(default_factory=list, description="Verified citations, e.g. ['resume.pdf (Page 1)']")
    is_grounded: bool = Field(True, description="True if answer was found, False if missing from documents")
    supporting_sources: List[SearchResult] = Field(
        default_factory=list,
        description="The raw retrieved document excerpts used to generate the answer",
    )
