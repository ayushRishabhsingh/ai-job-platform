"""Recommendation and skill-gap endpoints.

GET /recommendations            ranked jobs for the logged-in user
GET /jobs/{job_id}/skill-gap    what is missing for one specific job
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.config import settings
from app.core.deps import CurrentUser, DbSession
from app.models import Job
from app.schemas import JobRead, Recommendation, RecommendationResponse, SkillGap
from app.services.matcher import (
    MatchStrategy,
    TfidfMatcher,
    blend,
    embedding_available,
    embedding_scores,
    gap_advice,
    weighted_overlap,
)

router = APIRouter(tags=["recommendations"])


def _resume_text_for(user) -> str:
    """Text used by the semantic strategies; falls back to the skill list."""
    resume = user.active_resume
    if resume and resume.raw_text:
        return resume.raw_text
    return " ".join(user.all_skills)


@router.get(
    "/recommendations",
    response_model=RecommendationResponse,
    summary="Ranked job recommendations for the current user",
)
def get_recommendations(
    current_user: CurrentUser,
    db: DbSession,
    strategy: Annotated[
        MatchStrategy | None,
        Query(description="overlap (default, explainable) | tfidf | embedding"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    min_score: Annotated[float, Query(ge=0, le=100, description="Drop weaker matches")] = 0,
    location: Annotated[str | None, Query(description="Overrides your saved preference")] = None,
    max_experience: Annotated[
        int | None, Query(ge=0, description="Only jobs asking for at most N years")
    ] = None,
    candidate_pool: Annotated[
        int, Query(ge=10, le=1000, description="How many jobs to score before ranking")
    ] = 300,
) -> RecommendationResponse:
    user_skills = current_user.all_skills
    if not user_skills:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No skills on file. Upload a resume via POST /resumes/upload or add "
                "skills with PATCH /users/me before requesting recommendations."
            ),
        )

    chosen = strategy or MatchStrategy(settings.DEFAULT_MATCH_STRATEGY)

    # --- Build the candidate pool (cheap SQL filters first, scoring after) ---
    filters = [Job.is_active.is_(True)]
    effective_location = location or current_user.preferred_location
    if effective_location:
        filters.append(func.lower(Job.location).like(f"%{effective_location.lower()}%"))
    if max_experience is not None:
        filters.append(Job.experience_required <= max_experience)

    jobs = list(
        db.scalars(
            select(Job).where(*filters).order_by(Job.created_at.desc()).limit(candidate_pool)
        )
    )

    # A location preference that matches nothing would otherwise return an empty
    # list, which reads like a bug to the user. Fall back to the global pool.
    if not jobs and effective_location:
        jobs = list(
            db.scalars(
                select(Job)
                .where(Job.is_active.is_(True))
                .order_by(Job.created_at.desc())
                .limit(candidate_pool)
            )
        )

    if not jobs:
        return RecommendationResponse(
            strategy=chosen.value,
            user_skills_used=user_skills,
            total_jobs_scored=0,
            recommendations=[],
        )

    # --- Score ---
    overlaps = [
        weighted_overlap(
            user_skills, job.skills or [], current_user.years_experience, job.experience_required
        )
        for job in jobs
    ]

    if chosen == MatchStrategy.OVERLAP:
        results = overlaps
    else:
        resume_text = _resume_text_for(current_user)
        job_texts = [job.searchable_text for job in jobs]

        if chosen == MatchStrategy.TFIDF:
            semantic = TfidfMatcher(job_texts).scores_for(resume_text)
        else:
            if not embedding_available():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "The embedding strategy needs sentence-transformers. Install it "
                        "with `pip install sentence-transformers`, or use "
                        "?strategy=tfidf instead."
                    ),
                )
            semantic = embedding_scores(resume_text, job_texts, settings.EMBEDDING_MODEL)

        if len(semantic) != len(jobs):  # defensive: empty-corpus edge case
            semantic = [0.0] * len(jobs)
        results = [blend(sem, ov, chosen.value) for sem, ov in zip(semantic, overlaps, strict=True)]

    # --- Rank ---
    scored = [
        Recommendation(
            job_id=job.id,
            title=job.title,
            company=job.company,
            location=job.location,
            experience_required=job.experience_required,
            match_score=result.score,
            matched_skills=result.matched_skills,
            missing_skills=result.missing_skills,
            strategy=result.strategy,
        )
        for job, result in zip(jobs, results, strict=True)
        if result.score >= min_score
    ]
    # Tie-break on fewer missing skills, then newer job id.
    scored.sort(key=lambda r: (-r.match_score, len(r.missing_skills), -r.job_id))

    return RecommendationResponse(
        strategy=chosen.value,
        user_skills_used=user_skills,
        total_jobs_scored=len(jobs),
        recommendations=scored[:limit],
    )


@router.get(
    "/jobs/{job_id}/skill-gap",
    response_model=SkillGap,
    summary="Skill-gap analysis for one job",
)
def get_skill_gap(job_id: int, current_user: CurrentUser, db: DbSession) -> SkillGap:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

    user_skills = current_user.all_skills
    if not user_skills:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No skills on file. Upload a resume or add skills to your profile first.",
        )

    result = weighted_overlap(
        user_skills, job.skills or [], current_user.years_experience, job.experience_required
    )
    return SkillGap(
        job=JobRead.model_validate(job),
        match_score=result.score,
        matched_skills=result.matched_skills,
        missing_skills=result.missing_skills,
        coverage=result.coverage,
        advice=gap_advice(result.missing_skills, result.score),
    )
