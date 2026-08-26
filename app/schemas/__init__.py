"""Pydantic request/response schemas."""

from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationRead,
    ApplicationStats,
    ApplicationUpdate,
    StatusCount,
)
from app.schemas.common import HealthResponse, Message, Page
from app.schemas.job import JobCreate, JobRead, JobUpdate
from app.schemas.recommendation import Recommendation, RecommendationResponse, SkillGap
from app.schemas.resume import ResumeDetail, ResumeRead, ResumeUploadResponse, SkillPatch
from app.schemas.user import (
    LoginRequest,
    Token,
    TokenPayload,
    UserCreate,
    UserProfile,
    UserRead,
    UserUpdate,
)

__all__ = [
    "ApplicationCreate",
    "ApplicationDetail",
    "ApplicationRead",
    "ApplicationStats",
    "ApplicationUpdate",
    "StatusCount",
    "HealthResponse",
    "Message",
    "Page",
    "JobCreate",
    "JobRead",
    "JobUpdate",
    "Recommendation",
    "RecommendationResponse",
    "SkillGap",
    "ResumeDetail",
    "ResumeRead",
    "ResumeUploadResponse",
    "SkillPatch",
    "LoginRequest",
    "Token",
    "TokenPayload",
    "UserCreate",
    "UserProfile",
    "UserRead",
    "UserUpdate",
]
