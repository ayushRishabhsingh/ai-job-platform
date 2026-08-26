"""Business logic: resume parsing, skill extraction and job matching."""

from app.services.matcher import (
    MatchResult,
    MatchStrategy,
    TfidfMatcher,
    blend,
    confidence_label,
    embedding_available,
    embedding_scores,
    gap_advice,
    skill_overlap,
    weighted_overlap,
)
from app.services.resume_parser import ParsedResume, UnsupportedResumeFormat, parse_resume
from app.services.skill_extractor import extract_skills, extract_skills_with_counts

__all__ = [
    "MatchResult",
    "MatchStrategy",
    "TfidfMatcher",
    "blend",
    "confidence_label",
    "embedding_available",
    "embedding_scores",
    "gap_advice",
    "skill_overlap",
    "weighted_overlap",
    "ParsedResume",
    "UnsupportedResumeFormat",
    "parse_resume",
    "extract_skills",
    "extract_skills_with_counts",
]
