"""Resume upload and management.

The upload pipeline:

    PDF -> text extraction -> section split -> skill extraction -> database
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select

from app.config import settings
from app.core.deps import CurrentUser, DbSession, Pagination
from app.data.skills import canonicalise_all
from app.models import Resume
from app.schemas import Message, Page, ResumeDetail, ResumeRead, ResumeUploadResponse, SkillPatch
from app.services.resume_parser import UnsupportedResumeFormat, detect_kind, parse_resume
from app.services.skill_extractor import extract_skills

router = APIRouter(prefix="/resumes", tags=["resumes"])

CHUNK_SIZE = 1024 * 1024  # 1 MB


def get_own_resume_or_404(db, resume_id: int, user_id: int) -> Resume:
    resume = db.get(Resume, resume_id)
    if resume is None or resume.user_id != user_id:
        # 404 rather than 403, so the endpoint does not leak which ids exist.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Resume {resume_id} not found"
        )
    return resume


async def _save_upload(upload: UploadFile, dest: Path) -> int:
    """Stream the upload to disk, enforcing the size cap as we go."""
    size = 0
    with dest.open("wb") as buffer:
        while chunk := await upload.read(CHUNK_SIZE):
            size += len(chunk)
            if size > settings.max_upload_bytes:
                buffer.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit",
                )
            buffer.write(chunk)
    return size


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a resume (PDF, DOCX or TXT) and extract skills from it",
)
async def upload_resume(
    current_user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File(description="PDF, DOCX or TXT, max 5 MB")],
    make_active: Annotated[bool, Query(description="Use this resume for recommendations")] = True,
) -> ResumeUploadResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No filename provided"
        )

    # Reject unsupported formats before writing anything to disk.
    try:
        detect_kind(file.filename, file.content_type)
    except UnsupportedResumeFormat as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc

    suffix = Path(file.filename).suffix.lower()
    stored_name = f"user{current_user.id}_{uuid.uuid4().hex}{suffix}"
    dest = settings.UPLOAD_DIR / stored_name

    size = await _save_upload(file, dest)

    try:
        parsed = parse_resume(dest, filename=file.filename, content_type=file.content_type)
    except (UnsupportedResumeFormat, Exception) as exc:
        dest.unlink(missing_ok=True)
        if isinstance(exc, UnsupportedResumeFormat):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not read the file: {exc}",
        ) from exc

    skills = extract_skills(parsed.text, parsed.sections)

    if make_active:
        # Only one active resume per user.
        db.execute(
            Resume.__table__.update()
            .where(Resume.user_id == current_user.id)
            .values(is_active=False)
        )

    resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        stored_path=str(dest),
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        raw_text=parsed.text,
        skills=skills,
        page_count=parsed.page_count,
        word_count=parsed.word_count,
        is_active=make_active,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    message = (
        f"Extracted {len(skills)} skills from {parsed.word_count} words."
        if skills
        else "No known skills were recognised. Add them manually via PATCH /resumes/{id}/skills."
    )
    return ResumeUploadResponse(
        resume=ResumeRead.model_validate(resume),
        skills_found=len(skills),
        message=message,
    )


@router.get("", response_model=Page[ResumeRead], summary="List your resumes")
def list_resumes(
    current_user: CurrentUser, db: DbSession, pagination: Pagination
) -> Page[ResumeRead]:
    where = Resume.user_id == current_user.id
    total = db.scalar(select(func.count()).select_from(Resume).where(where)) or 0
    rows = list(
        db.scalars(
            select(Resume)
            .where(where)
            .order_by(Resume.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
    )
    return Page.build(
        items=[ResumeRead.model_validate(r) for r in rows],
        total=total,
        page=pagination.page,
        limit=pagination.limit,
    )


@router.get("/{resume_id}", response_model=ResumeDetail, summary="Get one resume")
def get_resume(
    resume_id: int,
    current_user: CurrentUser,
    db: DbSession,
    include_text: Annotated[bool, Query(description="Include the extracted plain text")] = False,
) -> ResumeDetail:
    resume = get_own_resume_or_404(db, resume_id, current_user.id)
    detail = ResumeDetail.model_validate(resume)
    if not include_text:
        detail.raw_text = None
    return detail


@router.post("/{resume_id}/activate", response_model=ResumeRead, summary="Set the active resume")
def activate_resume(resume_id: int, current_user: CurrentUser, db: DbSession) -> Resume:
    resume = get_own_resume_or_404(db, resume_id, current_user.id)
    db.execute(
        Resume.__table__.update().where(Resume.user_id == current_user.id).values(is_active=False)
    )
    resume.is_active = True
    db.commit()
    db.refresh(resume)
    return resume


@router.patch(
    "/{resume_id}/skills",
    response_model=ResumeRead,
    summary="Manually correct the extracted skill list",
)
def patch_skills(
    resume_id: int, payload: SkillPatch, current_user: CurrentUser, db: DbSession
) -> Resume:
    resume = get_own_resume_or_404(db, resume_id, current_user.id)

    current = list(resume.skills or [])
    remove = {s.strip().lower() for s in canonicalise_all(payload.remove)}
    current = [s for s in current if s.lower() not in remove]

    existing = {s.lower() for s in current}
    for skill in canonicalise_all(payload.add):
        if skill.lower() not in existing:
            current.append(skill)
            existing.add(skill.lower())

    # Reassign (do not mutate) so SQLAlchemy detects the change on a JSON column.
    resume.skills = current
    db.commit()
    db.refresh(resume)
    return resume


@router.delete("/{resume_id}", response_model=Message, summary="Delete a resume")
def delete_resume(resume_id: int, current_user: CurrentUser, db: DbSession) -> Message:
    resume = get_own_resume_or_404(db, resume_id, current_user.id)
    Path(resume.stored_path).unlink(missing_ok=True)
    db.delete(resume)
    db.commit()
    return Message(detail=f"Resume {resume_id} deleted")
