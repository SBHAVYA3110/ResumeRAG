"""
LLM Response Models.
Defines structured schemas for grounded Q&A responses and comprehensive skill match reports.
"""

from typing import List
from pydantic import BaseModel, Field


class AnswerWithCitations(BaseModel):
    """
    Represents a strictly grounded answer to a user query,
    backed by explicit document citations.
    """
    answer: str = Field(..., description="The factual answer grounded strictly in the provided context")
    citations: List[str] = Field(default_factory=list, description="List of source citations, e.g. ['doc.pdf (Page 1)']")
    is_grounded: bool = Field(True, description="True if the answer was found in the document, False if information was missing")


class SkillGapItem(BaseModel):
    """Represents a specific skill or qualification gap with an actionable remedy."""
    skill: str = Field(..., description="Name of the skill or requirement")
    status: str = Field(..., description="'Matched', 'Missing', or 'Partial'")
    recommendation: str = Field(..., description="Concrete advice to acquire or showcase this skill")


class SkillMatchReport(BaseModel):
    """
    Comprehensive comparison report evaluating a resume against a job description.
    """
    match_score: int = Field(..., ge=0, le=100, description="Overall match percentage from 0 to 100")
    candidate_name: str = Field("Candidate", description="Name of the candidate extracted from the resume")
    role_title: str = Field("Job Opening", description="Title of the target job position")
    summary: str = Field(..., description="Executive summary of the candidate's alignment with the role")
    matching_skills: List[str] = Field(default_factory=list, description="Skills present in both resume and job description")
    missing_skills: List[str] = Field(default_factory=list, description="Key skills required by the job that are absent from the resume")
    skill_gaps: List[SkillGapItem] = Field(default_factory=list, description="Detailed breakdown of each missing or partial skill")
    recommendations: List[str] = Field(default_factory=list, description="Actionable bullet points for tailoring the resume to the job")
