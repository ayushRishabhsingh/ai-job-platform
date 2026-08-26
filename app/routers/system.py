"""System endpoints: health check and skill taxonomy lookup."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import text

from app.config import settings
from app.core.deps import DbSession
from app.data.skills import ALL_SKILLS
from app.schemas import HealthResponse
from app.services.matcher import MatchStrategy, embedding_available

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, summary="Liveness / readiness probe")
def health(db: DbSession) -> HealthResponse:
    # Actually touch the database — a health check that only returns "ok"
    # tells a load balancer nothing useful.
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:  # pragma: no cover
        db_status = f"error: {type(exc).__name__}"

    strategies = [MatchStrategy.OVERLAP.value, MatchStrategy.TFIDF.value]
    if embedding_available():
        strategies.append(MatchStrategy.EMBEDDING.value)

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        database=db_status,
        match_strategies=strategies,
    )


@router.get("/skills", response_model=list[str], summary="Browse the skill taxonomy")
def list_skills(
    q: Annotated[str | None, Query(description="Filter by substring")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[str]:
    """Useful for autocomplete in the frontend."""
    skills = ALL_SKILLS
    if q:
        needle = q.lower()
        skills = [s for s in skills if needle in s.lower()]
    return skills[:limit]
