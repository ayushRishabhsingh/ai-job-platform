"""User profile endpoints."""

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.schemas import Message, UserProfile, UserUpdate

router = APIRouter(tags=["users"])


def _to_profile(user) -> UserProfile:
    resume = user.active_resume
    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        preferred_location=user.preferred_location,
        years_experience=user.years_experience,
        extra_skills=user.extra_skills or [],
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        all_skills=user.all_skills,
        active_resume_id=resume.id if resume else None,
    )


@router.get("/users/me", response_model=UserProfile, summary="Current user's profile")
def read_me(current_user: CurrentUser) -> UserProfile:
    return _to_profile(current_user)


@router.patch("/users/me", response_model=UserProfile, summary="Update profile / preferences")
def update_me(payload: UserUpdate, current_user: CurrentUser, db: DbSession) -> UserProfile:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return _to_profile(current_user)


@router.delete(
    "/users/me",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    summary="Delete own account (cascades to resumes and applications)",
)
def delete_me(current_user: CurrentUser, db: DbSession) -> Message:
    db.delete(current_user)
    db.commit()
    return Message(detail="Account deleted")
