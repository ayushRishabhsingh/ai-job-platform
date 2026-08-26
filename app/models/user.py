"""User model."""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.application import Application
    from app.models.job import Job
    from app.models.resume import Resume


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(120))

    # --- Job preferences, used by the recommendation engine ---
    preferred_location: Mapped[str | None] = mapped_column(String(120))
    years_experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Skills the user typed in manually, on top of whatever the resume parser found.
    extra_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Relationships ---
    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    posted_jobs: Mapped[list["Job"]] = relationship(back_populates="posted_by")

    # ------------------------------------------------------------------
    @property
    def active_resume(self) -> "Resume | None":
        for resume in self.resumes:
            if resume.is_active:
                return resume
        return None

    @property
    def all_skills(self) -> list[str]:
        """Resume skills + manually added skills, de-duplicated, order kept."""
        skills: list[str] = []
        seen: set[str] = set()
        resume = self.active_resume
        source = list(resume.skills if resume else []) + list(self.extra_skills or [])
        for skill in source:
            key = skill.strip().lower()
            if key and key not in seen:
                seen.add(key)
                skills.append(skill.strip())
        return skills

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email!r}>"
