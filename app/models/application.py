"""Application (job-tracker) model."""

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.job import Job
    from app.models.user import User


class ApplicationStatus(str, Enum):
    """Pipeline stages, in the order a candidate moves through them."""

    SAVED = "Saved"
    APPLIED = "Applied"
    OA = "OA"
    INTERVIEW = "Interview"
    REJECTED = "Rejected"
    OFFER = "Offer"


class Application(Base, TimestampMixin):
    __tablename__ = "applications"
    # A user can only track a given job once.
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )

    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus, native_enum=False, length=20),
        default=ApplicationStatus.SAVED,
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    # Snapshot of the match score at the time of saving, so history is preserved
    # even if the resume changes later.
    match_score_at_apply: Mapped[float | None] = mapped_column(Float)

    user: Mapped["User"] = relationship(back_populates="applications")
    job: Mapped["Job"] = relationship(back_populates="applications")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Application id={self.id} job_id={self.job_id} status={self.status}>"
