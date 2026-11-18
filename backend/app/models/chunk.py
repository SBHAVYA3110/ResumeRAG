"""
Chunk Models.
Defines structured data classes for text chunks and chunked documents.
"""

from typing import Any, Dict, List, Union
from pydantic import BaseModel, Field


class TextChunk(BaseModel):
    """
    Represents a discrete, semantically coherent segment of text from a document.
    Carries source metadata so citations can be traced back to the exact page.
    """
    chunk_id: str = Field(..., description="Unique deterministic identifier (e.g. doc.pdf_p1_c0)")
    text: str = Field(..., description="Text content of the chunk")
    source_doc: str = Field(..., description="Original filename of the document")
    page_number: int = Field(..., description="1-indexed page number where this chunk originated")
    chunk_index: int = Field(..., description="Sequential index of this chunk within the page/doc")
    char_count: int = Field(..., description="Length of chunk text in characters")

    @property
    def metadata(self) -> Dict[str, Union[str, int]]:
        """Convenience dictionary formatted for ChromaDB metadata storage."""
        return {
            "chunk_id": self.chunk_id,
            "source": self.source_doc,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "char_count": self.char_count,
        }


class ChunkedDocument(BaseModel):
    """Represents a fully chunked document ready for embedding and vector storage."""
    filename: str = Field(..., description="Original filename of the document")
    total_chunks: int = Field(..., description="Total number of chunks produced")
    chunks: List[TextChunk] = Field(default_factory=list, description="List of generated text chunks")


class SearchResult(BaseModel):
    """
    Represents a chunk retrieved from ChromaDB in response to a semantic query.
    Includes the relevance similarity score and page citation metadata.
    """
    chunk_id: str = Field(..., description="Unique chunk identifier")
    text: str = Field(..., description="Retrieved chunk text content")
    source_doc: str = Field(..., description="Filename of the source document")
    page_number: int = Field(..., description="Page number where the text appears")
    chunk_index: int = Field(..., description="Index of the chunk in the document")
    distance: float = Field(..., description="Cosine distance from ChromaDB (0.0 = exact match)")
    similarity_score: float = Field(..., description="Normalized similarity score (1.0 = exact match)")
