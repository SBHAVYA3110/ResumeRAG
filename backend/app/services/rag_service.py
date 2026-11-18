"""
Unified RAG Pipeline Service.
Orchestrates PDF text extraction, chunking, vector storage, and Gemini generation
into a cohesive, high-level interface.
"""

from pathlib import Path
from typing import BinaryIO, List, Optional, Union

from backend.app.models.llm import SkillMatchReport
from backend.app.models.rag import IngestionResponse, QueryResponse
from backend.app.services.chunking_service import chunk_document
from backend.app.services.llm_service import LLMService, get_llm_service
from backend.app.services.pdf_service import extract_text_from_pdf
from backend.app.services.vector_store_service import (
    VectorStoreService,
    get_vector_store_service,
)


class RAGPipeline:
    """
    Facade controller for the ResumeRAG application.
    Coordinates document ingestion, conversational question answering,
    and resume-job description skill gap analysis.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStoreService] = None,
        llm_service: Optional[LLMService] = None,
    ):
        self.vector_store = vector_store or get_vector_store_service()
        self.llm_service = llm_service or get_llm_service()

    def ingest_document(
        self,
        source: Union[str, Path, BinaryIO, bytes],
        filename: str = "document.pdf",
        chunk_size: int = 400,
        chunk_overlap: int = 80,
    ) -> IngestionResponse:
        """
        End-to-End Ingestion Workflow:
        1. Extracts text and page metadata from PDF.
        2. Recursively chunks the text with natural boundary preservation.
        3. Generates 768-dim embeddings and upserts chunks into ChromaDB.
        """
        # Step 1: Extract PDF pages
        extracted_doc = extract_text_from_pdf(source=source, filename=filename)

        # Step 2: Chunk pages into coherent text snippets
        chunked_doc = chunk_document(
            document=extracted_doc,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Step 3: Embed and store in ChromaDB
        total_chunks = self.vector_store.upsert_document(chunked_doc)

        return IngestionResponse(
            filename=extracted_doc.filename,
            total_pages=extracted_doc.total_pages,
            total_chunks=total_chunks,
            message=(
                f"Successfully ingested '{extracted_doc.filename}': "
                f"{extracted_doc.total_pages} pages parsed into {total_chunks} indexed vector chunks."
            ),
        )

    def ask(
        self,
        query: str,
        document_filter: Optional[str] = None,
        n_results: int = 8,
    ) -> QueryResponse:
        """
        End-to-End Grounded Q&A Workflow:
        1. Embeds the user question into a vector.
        2. Retrieves the top-n most relevant chunks from ChromaDB.
        3. Formulates a grounded context prompt for Gemini.
        4. Returns the answer with verified document citations.
        """
        where_filter = {"source": document_filter} if document_filter else None

        # Step 1 & 2: Retrieve relevant chunks from vector store
        supporting_chunks = self.vector_store.query_similar(
            query_text=query,
            n_results=n_results,
            where_filter=where_filter,
        )

        # Step 3 & 4: Generate grounded answer with citations
        ans_with_citations = self.llm_service.generate_grounded_answer(
            query=query,
            context_chunks=supporting_chunks,
        )

        return QueryResponse(
            query=query,
            answer=ans_with_citations.answer,
            citations=ans_with_citations.citations,
            is_grounded=ans_with_citations.is_grounded,
            supporting_sources=supporting_chunks,
        )

    def compare_resume_and_job(
        self,
        resume_filename: str,
        job_filename: str,
        max_chunks_per_doc: int = 8,
    ) -> SkillMatchReport:
        """
        End-to-End Resume vs. Job Match Workflow:
        1. Retrieves indexed chunks for both the resume and the job description.
        2. Validates that both documents have been uploaded and processed.
        3. Feeds both context sets into Gemini for deep semantic gap analysis.
        4. Returns a comprehensive SkillMatchReport (score, matching skills, gaps, advice).
        """
        # Retrieve resume chunks
        resume_chunks = self.vector_store.query_similar(
            query_text="candidate experience technical skills frameworks projects",
            n_results=max_chunks_per_doc,
            where_filter={"source": resume_filename},
        )
        if not resume_chunks:
            raise ValueError(
                f"No indexed content found for resume: '{resume_filename}'. "
                "Please upload and ingest the resume before running comparison."
            )

        # Retrieve job description chunks
        job_chunks = self.vector_store.query_similar(
            query_text="job requirements qualifications responsibilities skills",
            n_results=max_chunks_per_doc,
            where_filter={"source": job_filename},
        )
        if not job_chunks:
            raise ValueError(
                f"No indexed content found for job description: '{job_filename}'. "
                "Please upload and ingest the job description before running comparison."
            )

        # Generate deep comparison report
        return self.llm_service.generate_match_report(
            resume_chunks=resume_chunks,
            job_chunks=job_chunks,
        )

    def delete_document(self, filename: str) -> None:
        """Removes a document and all its vector chunks from the database."""
        self.vector_store.delete_document(filename)


# Singleton helper
_default_rag_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    """Returns a shared singleton instance of the RAGPipeline."""
    global _default_rag_pipeline
    if _default_rag_pipeline is None:
        _default_rag_pipeline = RAGPipeline()
    return _default_rag_pipeline
