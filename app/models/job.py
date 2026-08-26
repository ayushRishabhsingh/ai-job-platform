"""Job model."""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.application import Application
    from app.models.user import User


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    company: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    location: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Required skills, stored as a JSON array: ["Python", "FastAPI", ...]
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    experience_required: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    employment_type: Mapped[str] = mapped_column(String(40), default="Full-time", nullable=False)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    posted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    # --- Relationships ---
    posted_by: Mapped["User | None"] = relationship(back_populates="posted_jobs")
    applications: Mapped[list["Application"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------
    @property
    def searchable_text(self) -> str:
        """Concatenated text used by the TF-IDF / embedding matchers."""
        parts = [self.title, self.company, self.location, self.description or ""]
        parts.extend(self.skills or [])
        return " ".join(p for p in parts if p)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Job id={self.id} title={self.title!r} company={self.company!r}>"
