"""
Database History Service.
Handles CRUD operations for document metadata, comparison records, and chat conversation history.
"""

import json
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.models.db_models import (
    ChatMessageRecord,
    ComparisonRecord,
    DocumentRecord,
)
from backend.app.models.llm import SkillMatchReport


class HistoryService:
    """Service encapsulating all relational database queries and mutations."""

    @staticmethod
    def record_document(
        db: Session,
        filename: str,
        total_pages: int,
        total_chunks: int,
        file_size_bytes: int = 0,
        doc_type: str = "unknown",
    ) -> DocumentRecord:
        """Saves or updates metadata for an uploaded document."""
        existing = db.query(DocumentRecord).filter(DocumentRecord.filename == filename).first()
        if existing:
            existing.total_pages = total_pages
            existing.total_chunks = total_chunks
            existing.file_size_bytes = file_size_bytes
            existing.doc_type = doc_type
            db.commit()
            db.refresh(existing)
            return existing

        record = DocumentRecord(
            filename=filename,
            doc_type=doc_type,
            total_pages=total_pages,
            total_chunks=total_chunks,
            file_size_bytes=file_size_bytes,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def list_documents(db: Session) -> List[DocumentRecord]:
        """Lists all uploaded documents ordered by upload date descending."""
        return db.query(DocumentRecord).order_by(DocumentRecord.uploaded_at.desc()).all()

    @staticmethod
    def delete_document_record(db: Session, filename: str) -> bool:
        """Deletes a document record from the database."""
        record = db.query(DocumentRecord).filter(DocumentRecord.filename == filename).first()
        if record:
            db.delete(record)
            db.commit()
            return True
        return False

    @staticmethod
    def record_comparison(
        db: Session,
        report: SkillMatchReport,
        resume_filename: str,
        job_filename: str,
    ) -> ComparisonRecord:
        """Persists a generated skill match report into the database."""
        record = ComparisonRecord(
            resume_filename=resume_filename,
            job_filename=job_filename,
            candidate_name=report.candidate_name,
            role_title=report.role_title,
            match_score=report.match_score,
            summary=report.summary,
            matching_skills_json=json.dumps(report.matching_skills),
            missing_skills_json=json.dumps(report.missing_skills),
            recommendations_json=json.dumps(report.recommendations),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def list_comparisons(db: Session, limit: int = 20) -> List[ComparisonRecord]:
        """Fetches past comparison reports ordered from newest to oldest."""
        return (
            db.query(ComparisonRecord)
            .order_by(ComparisonRecord.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def record_chat_message(
        db: Session,
        query: str,
        answer: str,
        citations: List[str],
        is_grounded: bool,
        document_filter: Optional[str] = None,
    ) -> ChatMessageRecord:
        """Logs a conversational Q&A exchange with source citations."""
        record = ChatMessageRecord(
            query=query,
            answer=answer,
            citations_json=json.dumps(citations),
            is_grounded=is_grounded,
            document_filter=document_filter,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def list_chat_messages(db: Session, limit: int = 50) -> List[ChatMessageRecord]:
        """Fetches recent chat logs ordered by creation timestamp."""
        return (
            db.query(ChatMessageRecord)
            .order_by(ChatMessageRecord.created_at.desc())
            .limit(limit)
            .all()
        )
