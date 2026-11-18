"""
FastAPI Route Endpoints.
Defines REST endpoints for document upload, conversational Q&A, and resume-job comparison.
"""

import os
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.document import (
    EmptyPDFError,
    EncryptedPDFError,
    PDFExtractionError,
)
from backend.app.models.llm import SkillMatchReport
from backend.app.models.rag import IngestionResponse, QueryResponse
from backend.app.models.requests import ChatRequest, MatchRequest
from backend.app.services.history_service import HistoryService
from backend.app.services.rag_service import RAGPipeline, get_rag_pipeline

router = APIRouter(prefix="/api", tags=["ResumeRAG Endpoints"])

# Security Constants
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB maximum allowed PDF file size


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes an uploaded filename to defend against Directory Traversal attacks.
    Strips directory separators, relative path markers (../, ..\\), and illegal characters.
    """
    # 1. Extract purely the base name without leading directory segments
    base = os.path.basename(filename.strip().replace("\\", "/"))
    # 2. Strip any remaining path traversal tokens
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', base)
    if not clean:
        clean = "document.pdf"
    return clean


# ==============================================================================
# Health Check Endpoint
# ==============================================================================

@router.get(
    "/health",
    summary="Service Health Check",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> Dict[str, str]:
    """Returns the operational status of the ResumeRAG backend."""
    return {
        "status": "healthy",
        "service": "ResumeRAG API",
        "version": "1.0.0",
    }


# ==============================================================================
# Document Upload & Ingestion Endpoint
# ==============================================================================

@router.post(
    "/documents/upload",
    summary="Upload & Index a PDF Document",
    response_model=IngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file (Resume or Job Description)"),
    db: Session = Depends(get_db),
) -> IngestionResponse:
    """
    Uploads a PDF document, extracts its text, chunks it, indexes it in ChromaDB,
    and logs metadata in the relational database.
    """
    # Step 1: Validate file extension & defend against directory traversal
    raw_filename = file.filename or "uploaded_document.pdf"
    if not raw_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type for '{raw_filename}'. Only PDF files (.pdf) are supported.",
        )
    filename = sanitize_filename(raw_filename)

    # Step 2: Ingest file into RAG pipeline
    pipeline: RAGPipeline = get_rag_pipeline()
    try:
        # Read the uploaded file bytes
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The uploaded file '{filename}' is empty (0 bytes).",
            )
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"The uploaded file '{filename}' exceeds the maximum allowed size of 10 MB ({len(file_bytes)} bytes).",
            )

        ingestion_result = pipeline.ingest_document(
            source=file_bytes,
            filename=filename,
        )

        # Step 3: Record document metadata in PostgreSQL / SQLite
        doc_type = (
            "resume"
            if "resume" in filename.lower()
            else ("job_description" if "job" in filename.lower() or "jd" in filename.lower() else "general")
        )
        HistoryService.record_document(
            db=db,
            filename=filename,
            total_pages=ingestion_result.total_pages,
            total_chunks=ingestion_result.total_chunks,
            file_size_bytes=len(file_bytes),
            doc_type=doc_type,
        )

        return ingestion_result

    except HTTPException:
        raise
    except EncryptedPDFError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except EmptyPDFError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except PDFExtractionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process PDF: {str(e)}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during document ingestion: {str(e)}",
        ) from e
    finally:
        await file.close()


# ==============================================================================
# Document Deletion Endpoint
# ==============================================================================

@router.delete(
    "/documents/{filename}",
    summary="Delete a Document and its Vector Chunks",
    status_code=status.HTTP_200_OK,
)
async def delete_document(
    filename: str,
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Purges a document and all its indexed vector chunks from ChromaDB and the database."""
    pipeline: RAGPipeline = get_rag_pipeline()
    try:
        clean_filename = sanitize_filename(filename)
        pipeline.delete_document(clean_filename)
        HistoryService.delete_document_record(db, clean_filename)
        return {
            "status": "success",
            "message": f"Successfully deleted document '{clean_filename}' from vector database.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        ) from e


# ==============================================================================
# Conversational Q&A (Chat) Endpoint
# ==============================================================================

@router.post(
    "/chat",
    summary="Ask a Question Grounded in Uploaded Documents",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
)
async def chat_with_documents(
    payload: ChatRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    """
    Retrieves the most semantically relevant document chunks and generates
    a strictly grounded answer with citations.
    """
    pipeline: RAGPipeline = get_rag_pipeline()
    try:
        response = pipeline.ask(
            query=payload.query,
            document_filter=payload.document_filter,
            n_results=payload.n_results,
        )
        HistoryService.record_chat_message(
            db=db,
            query=payload.query,
            answer=response.answer,
            citations=response.citations,
            is_grounded=response.is_grounded,
            document_filter=payload.document_filter,
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating answer: {str(e)}",
        ) from e


# ==============================================================================
# Resume vs. Job Description Matching Endpoint
# ==============================================================================

@router.post(
    "/match",
    summary="Compare Resume Against Job Description",
    response_model=SkillMatchReport,
    status_code=status.HTTP_200_OK,
)
async def compare_resume_to_job(
    payload: MatchRequest,
    db: Session = Depends(get_db),
) -> SkillMatchReport:
    """
    Performs deep semantic comparison between an uploaded resume and job description.
    Returns match score, matched skills, missing skills, and tailored advice.
    """
    pipeline: RAGPipeline = get_rag_pipeline()
    try:
        report = pipeline.compare_resume_and_job(
            resume_filename=payload.resume_filename,
            job_filename=payload.job_filename,
        )
        HistoryService.record_comparison(
            db=db,
            report=report,
            resume_filename=payload.resume_filename,
            job_filename=payload.job_filename,
        )
        return report
    except HTTPException:
        raise
    except ValueError as e:
        # Document not found in vector store
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error comparing documents: {str(e)}",
        ) from e


# ==============================================================================
# Document Listing Endpoint
# ==============================================================================

@router.get(
    "/documents",
    summary="List All Ingested Documents",
    status_code=status.HTTP_200_OK,
)
async def list_documents(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Retrieves all tracked documents from the relational database."""
    docs = HistoryService.list_documents(db)
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "doc_type": d.doc_type,
            "total_pages": d.total_pages,
            "total_chunks": d.total_chunks,
            "file_size_bytes": d.file_size_bytes,
            "uploaded_at": d.uploaded_at.isoformat(),
        }
        for d in docs
    ]


# ==============================================================================
# Comparison History Endpoint
# ==============================================================================

@router.get(
    "/history/matches",
    summary="Retrieve Past Resume-Job Comparisons",
    status_code=status.HTTP_200_OK,
)
async def get_match_history(
    limit: int = Query(20, ge=1, le=100, description="Max records to retrieve"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Returns past skill match comparison reports ordered newest first."""
    records = HistoryService.list_comparisons(db, limit=limit)
    return [
        {
            "id": r.id,
            "resume_filename": r.resume_filename,
            "job_filename": r.job_filename,
            "candidate_name": r.candidate_name,
            "role_title": r.role_title,
            "match_score": r.match_score,
            "summary": r.summary,
            "matching_skills": r.matching_skills,
            "missing_skills": r.missing_skills,
            "recommendations": r.recommendations,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


# ==============================================================================
# Chat Conversation History Endpoint
# ==============================================================================

@router.get(
    "/history/chat",
    summary="Retrieve Chat Q&A History",
    status_code=status.HTTP_200_OK,
)
async def get_chat_history(
    limit: int = Query(50, ge=1, le=100, description="Max messages to retrieve"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Returns previous conversation questions, answers, and citations."""
    messages = HistoryService.list_chat_messages(db, limit=limit)
    return [
        {
            "id": m.id,
            "query": m.query,
            "answer": m.answer,
            "citations": m.citations,
            "is_grounded": m.is_grounded,
            "document_filter": m.document_filter,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]
