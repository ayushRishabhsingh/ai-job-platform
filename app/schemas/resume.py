"""Resume schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    filename: str
    content_type: str
    size_bytes: int
    skills: list[str]
    page_count: int
    word_count: int
    is_active: bool
    created_at: datetime


class ResumeDetail(ResumeRead):
    """Includes the extracted plain text — can be large, so it is opt-in."""

    raw_text: str | None = None


class ResumeUploadResponse(BaseModel):
    resume: ResumeRead
    skills_found: int
    message: str


class SkillPatch(BaseModel):
    """Manually add or remove skills on a parsed resume."""

    add: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)
