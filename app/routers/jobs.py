"""Job CRUD + search.

This is the router that teaches the REST fundamentals: path params,
query params, filtering, sorting, pagination and correct status codes.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import String, cast, func, or_, select

from app.core.deps import CurrentUser, DbSession, Pagination
from app.models import Job
from app.schemas import JobCreate, JobRead, JobUpdate, Message, Page

router = APIRouter(prefix="/jobs", tags=["jobs"])

SORT_COLUMNS = {
    "created_at": Job.created_at,
    "title": Job.title,
    "company": Job.company,
    "experience": Job.experience_required,
    "salary": Job.salary_max,
}


def skill_filter(skill: str):
    """Match one skill inside the JSON array column.

    The JSON column is cast to text and searched for the quoted skill name,
    which behaves identically on SQLite and PostgreSQL. With Postgres only you
    could use the native `?` / `@>` JSONB operators instead, which are indexable.
    """
    return func.lower(cast(Job.skills, String)).like(f'%"{skill.strip().lower()}"%')


def get_job_or_404(db, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")
    return job


@router.get("", response_model=Page[JobRead], summary="List / search jobs")
def list_jobs(
    db: DbSession,
    pagination: Pagination,
    q: Annotated[
        str | None, Query(description="Free text over title, company, description")
    ] = None,
    location: Annotated[str | None, Query(description="Case-insensitive partial match")] = None,
    company: str | None = None,
    skill: Annotated[
        list[str] | None,
        Query(description="Repeatable: ?skill=Python&skill=AWS (matches ALL given skills)"),
    ] = None,
    min_experience: Annotated[int | None, Query(ge=0)] = None,
    max_experience: Annotated[int | None, Query(ge=0)] = None,
    employment_type: str | None = None,
    is_active: bool = True,
    sort_by: Literal["created_at", "title", "company", "experience", "salary"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
) -> Page[JobRead]:
    stmt = select(Job)
    filters = [Job.is_active == is_active]

    if q:
        pattern = f"%{q.lower()}%"
        filters.append(
            or_(
                func.lower(Job.title).like(pattern),
                func.lower(Job.company).like(pattern),
                func.lower(func.coalesce(Job.description, "")).like(pattern),
            )
        )
    if location:
        filters.append(func.lower(Job.location).like(f"%{location.lower()}%"))
    if company:
        filters.append(func.lower(Job.company).like(f"%{company.lower()}%"))
    if skill:
        filters.extend(skill_filter(s) for s in skill if s.strip())
    if min_experience is not None:
        filters.append(Job.experience_required >= min_experience)
    if max_experience is not None:
        filters.append(Job.experience_required <= max_experience)
    if employment_type:
        filters.append(func.lower(Job.employment_type) == employment_type.lower())

    stmt = stmt.where(*filters)

    total = db.scalar(select(func.count()).select_from(Job).where(*filters)) or 0

    column = SORT_COLUMNS[sort_by]
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())
    stmt = stmt.offset(pagination.offset).limit(pagination.limit)

    jobs = list(db.scalars(stmt))
    return Page.build(
        items=[JobRead.model_validate(j) for j in jobs],
        total=total,
        page=pagination.page,
        limit=pagination.limit,
    )


@router.get("/{job_id}", response_model=JobRead, summary="Get one job")
def get_job(job_id: int, db: DbSession) -> Job:
    return get_job_or_404(db, job_id)


@router.post(
    "",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job posting",
)
def create_job(payload: JobCreate, current_user: CurrentUser, db: DbSession) -> Job:
    job = Job(**payload.model_dump(), posted_by_id=current_user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.put("/{job_id}", response_model=JobRead, summary="Update a job (partial body allowed)")
def update_job(job_id: int, payload: JobUpdate, current_user: CurrentUser, db: DbSession) -> Job:
    job = get_job_or_404(db, job_id)
    if job.posted_by_id not in (None, current_user.id) and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only edit jobs you posted"
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, field, value)

    # Re-run the cross-field salary check after the merge.
    if (
        job.salary_min is not None
        and job.salary_max is not None
        and job.salary_max < job.salary_min
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="salary_max must be greater than or equal to salary_min",
        )

    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", response_model=Message, summary="Delete a job")
def delete_job(job_id: int, current_user: CurrentUser, db: DbSession) -> Message:
    job = get_job_or_404(db, job_id)
    if job.posted_by_id not in (None, current_user.id) and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete jobs you posted"
        )
    db.delete(job)
    db.commit()
    return Message(detail=f"Job {job_id} deleted")
