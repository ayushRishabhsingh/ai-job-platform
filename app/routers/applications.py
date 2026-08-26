"""Application tracking: Saved -> Applied -> OA -> Interview -> Offer/Rejected."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession, Pagination
from app.models import Application, ApplicationStatus, Job
from app.schemas import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationStats,
    ApplicationUpdate,
    Message,
    Page,
    StatusCount,
)
from app.services.matcher import weighted_overlap

router = APIRouter(prefix="/applications", tags=["applications"])

# Statuses that count as the company having engaged with you.
RESPONDED = {ApplicationStatus.OA, ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER}


def get_own_application_or_404(db, application_id: int, user_id: int) -> Application:
    app_row = db.get(Application, application_id)
    if app_row is None or app_row.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found",
        )
    return app_row


@router.post(
    "",
    response_model=ApplicationDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Save or apply to a job",
)
def create_application(
    payload: ApplicationCreate, current_user: CurrentUser, db: DbSession
) -> Application:
    job = db.get(Job, payload.job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {payload.job_id} not found"
        )

    existing = db.scalar(
        select(Application).where(
            Application.user_id == current_user.id, Application.job_id == payload.job_id
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"You are already tracking this job as application {existing.id} "
                f"(status: {existing.status.value}). Use PUT to change its status."
            ),
        )

    # Snapshot the score now, so the history stays honest after resume edits.
    score = None
    if current_user.all_skills:
        score = weighted_overlap(
            current_user.all_skills,
            job.skills or [],
            current_user.years_experience,
            job.experience_required,
        ).score

    application = Application(
        user_id=current_user.id,
        job_id=payload.job_id,
        status=payload.status,
        notes=payload.notes,
        match_score_at_apply=score,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("", response_model=Page[ApplicationDetail], summary="List your applications")
def list_applications(
    current_user: CurrentUser,
    db: DbSession,
    pagination: Pagination,
    status_filter: Annotated[
        ApplicationStatus | None, Query(alias="status", description="Filter by pipeline stage")
    ] = None,
    sort_by: Literal["created_at", "updated_at", "match_score"] = "updated_at",
    order: Literal["asc", "desc"] = "desc",
) -> Page[ApplicationDetail]:
    filters = [Application.user_id == current_user.id]
    if status_filter:
        filters.append(Application.status == status_filter)

    total = db.scalar(select(func.count()).select_from(Application).where(*filters)) or 0

    columns = {
        "created_at": Application.created_at,
        "updated_at": Application.updated_at,
        "match_score": Application.match_score_at_apply,
    }
    column = columns[sort_by]

    rows = list(
        db.scalars(
            select(Application)
            .where(*filters)
            .options(selectinload(Application.job))  # avoids the N+1 on job
            .order_by(column.desc() if order == "desc" else column.asc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
    )
    return Page.build(
        items=[ApplicationDetail.model_validate(r) for r in rows],
        total=total,
        page=pagination.page,
        limit=pagination.limit,
    )


@router.get("/stats", response_model=ApplicationStats, summary="Funnel summary")
def get_stats(current_user: CurrentUser, db: DbSession) -> ApplicationStats:
    rows = db.execute(
        select(Application.status, func.count())
        .where(Application.user_id == current_user.id)
        .group_by(Application.status)
    ).all()

    counts = dict.fromkeys(ApplicationStatus, 0)
    for status_value, count in rows:
        counts[status_value] = count

    total = sum(counts.values())
    # "Applied" is the funnel entry point: anyone at OA or beyond also applied.
    applied_or_beyond = counts[ApplicationStatus.APPLIED] + sum(counts[s] for s in RESPONDED)
    responded = sum(counts[s] for s in RESPONDED)
    response_rate = round(responded / applied_or_beyond * 100, 1) if applied_or_beyond else 0.0

    return ApplicationStats(
        total=total,
        by_status=[StatusCount(status=s, count=counts[s]) for s in ApplicationStatus],
        response_rate=response_rate,
    )


@router.get("/{application_id}", response_model=ApplicationDetail, summary="Get one application")
def get_application(application_id: int, current_user: CurrentUser, db: DbSession) -> Application:
    return get_own_application_or_404(db, application_id, current_user.id)


@router.put("/{application_id}", response_model=ApplicationDetail, summary="Update status or notes")
def update_application(
    application_id: int, payload: ApplicationUpdate, current_user: CurrentUser, db: DbSession
) -> Application:
    application = get_own_application_or_404(db, application_id, current_user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(application, field, value)
    db.commit()
    db.refresh(application)
    return application


@router.delete("/{application_id}", response_model=Message, summary="Stop tracking a job")
def delete_application(application_id: int, current_user: CurrentUser, db: DbSession) -> Message:
    application = get_own_application_or_404(db, application_id, current_user.id)
    db.delete(application)
    db.commit()
    return Message(detail=f"Application {application_id} deleted")
