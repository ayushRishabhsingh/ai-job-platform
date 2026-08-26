"""User, auth and token schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=120)
    preferred_location: str | None = Field(default=None, max_length=120)
    years_experience: int = Field(default=0, ge=0, le=60)
    extra_skills: list[str] = Field(default_factory=list)

    @field_validator("extra_skills")
    @classmethod
    def clean_skills(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for s in v:
            s = s.strip()
            if s and s.lower() not in seen:
                seen.add(s.lower())
                out.append(s)
        return out


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class UserUpdate(BaseModel):
    """Everything optional — this is a partial update."""

    full_name: str | None = Field(default=None, max_length=120)
    preferred_location: str | None = Field(default=None, max_length=120)
    years_experience: int | None = Field(default=None, ge=0, le=60)
    extra_skills: list[str] | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime


class UserProfile(UserRead):
    """UserRead + the derived skill set actually used for matching."""

    all_skills: list[str] = Field(default_factory=list)
    active_resume_id: int | None = None


class LoginRequest(BaseModel):
    """JSON login body (the OAuth2 form flow is also supported)."""

    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds")


class TokenPayload(BaseModel):
    sub: str
    exp: int
