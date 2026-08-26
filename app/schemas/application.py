"""Application (tracker) schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.application import ApplicationStatus
from app.schemas.job import JobRead


class ApplicationCreate(BaseModel):
    job_id: int = Field(gt=0)
    status: ApplicationStatus = ApplicationStatus.SAVED
    notes: str | None = Field(default=None, max_length=5000)


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = Field(default=None, max_length=5000)


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    job_id: int
    status: ApplicationStatus
    notes: str | None
    match_score_at_apply: float | None
    created_at: datetime
    updated_at: datetime


class ApplicationDetail(ApplicationRead):
    """Nested job object, so the frontend needs one call instead of N+1."""

    job: JobRead


class StatusCount(BaseModel):
    status: ApplicationStatus
    count: int


class ApplicationStats(BaseModel):
    total: int
    by_status: list[StatusCount]
    response_rate: float = Field(description="(OA + Interview + Offer) / Applied, as a percentage")
