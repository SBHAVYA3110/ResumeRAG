"""
SQLAlchemy ORM Database Models.
Defines relational schemas for uploaded documents, comparison history, and conversational chat logs.
"""

from datetime import datetime, timezone
import json
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


def get_utc_now() -> datetime:
    """Returns current UTC timestamp without timezone offset for database compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DocumentRecord(Base):
    """Tracks metadata of uploaded PDF documents."""
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)
    total_pages: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)


class ComparisonRecord(Base):
    """Persists match scores and skill gap analyses between resumes and job descriptions."""
    __tablename__ = "comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    resume_filename: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    job_filename: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    candidate_name: Mapped[str] = mapped_column(String(255), default="Candidate", nullable=False)
    role_title: Mapped[str] = mapped_column(String(255), default="Job Opening", nullable=False)
    match_score: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    matching_skills_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    missing_skills_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    recommendations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)

    @property
    def matching_skills(self) -> List[str]:
        """Convenience property decoding JSON list of matching skills."""
        return json.loads(self.matching_skills_json)

    @property
    def missing_skills(self) -> List[str]:
        """Convenience property decoding JSON list of missing skills."""
        return json.loads(self.missing_skills_json)

    @property
    def recommendations(self) -> List[str]:
        """Convenience property decoding JSON list of recommendations."""
        return json.loads(self.recommendations_json)


class ChatMessageRecord(Base):
    """Logs conversation queries, grounded answers, and document citations."""
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    is_grounded: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    document_filter: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)

    @property
    def citations(self) -> List[str]:
        """Convenience property decoding JSON list of citations."""
        return json.loads(self.citations_json)
