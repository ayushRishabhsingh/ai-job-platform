"""Job schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _normalise_skills(v: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in v:
        s = s.strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


class JobBase(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    company: str = Field(min_length=1, max_length=160)
    location: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=20000)
    skills: list[str] = Field(default_factory=list)
    experience_required: int = Field(default=0, ge=0, le=40)
    employment_type: str = Field(default="Full-time", max_length=40)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, v: list[str]) -> list[str]:
        return _normalise_skills(v)

    @model_validator(mode="after")
    def check_salary_range(self):
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_max < self.salary_min
        ):
            raise ValueError("salary_max must be greater than or equal to salary_min")
        return self


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    """Partial update — send only the fields you want to change."""

    title: str | None = Field(default=None, min_length=2, max_length=160)
    company: str | None = Field(default=None, min_length=1, max_length=160)
    location: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=20000)
    skills: list[str] | None = None
    experience_required: int | None = Field(default=None, ge=0, le=40)
    employment_type: str | None = Field(default=None, max_length=40)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, v: list[str] | None) -> list[str] | None:
        return _normalise_skills(v) if v is not None else None


class JobRead(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    posted_by_id: int | None = None
    created_at: datetime
    updated_at: datetime
