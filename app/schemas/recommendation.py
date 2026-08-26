"""Recommendation and skill-gap schemas."""

from pydantic import BaseModel, Field

from app.schemas.job import JobRead


class Recommendation(BaseModel):
    job_id: int
    title: str
    company: str
    location: str
    experience_required: int
    match_score: float = Field(ge=0, le=100, description="0-100 match percentage")
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    strategy: str


class RecommendationResponse(BaseModel):
    strategy: str
    user_skills_used: list[str]
    total_jobs_scored: int
    recommendations: list[Recommendation]


class SkillGap(BaseModel):
    job: JobRead
    match_score: float = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    coverage: str = Field(description="Human-readable ratio, e.g. '4/6 skills'")
    advice: list[str] = Field(
        default_factory=list, description="Suggested next steps to close the gap"
    )
