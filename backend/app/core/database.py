"""
Database Configuration & Session Management.
Sets up SQLAlchemy 2.0 engine, declarative base, session factory, and FastAPI get_db dependency.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.core.config import get_settings

settings = get_settings()

# Step 1: Create Database Engine
# If using SQLite, check_same_thread=False allows FastAPI multi-threading
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,  # Set to True if you want to inspect raw SQL statements in console
)

# Step 2: Session Factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# Step 3: Modern SQLAlchemy 2.0 Declarative Base
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# Step 4: FastAPI Dependency for Database Sessions
def get_db() -> Generator[Session, None, None]:
    """
    Yields a database session per HTTP request and ensures it is cleanly closed.
    
    Why this pattern?
    It guarantees that every request gets its own isolated database transaction.
    When the request finishes (even if an error occurs), the 'finally' block
    closes the session, preventing database connection leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Creates all defined database tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)
