"""Authentication endpoints: /auth/register, /auth/login, /auth/token."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.core.deps import DbSession
from app.core.security import (
    create_access_token,
    hash_password,
    token_lifetime_seconds,
    verify_password,
)
from app.models import User
from app.schemas import LoginRequest, Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def _authenticate(db, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    # Same error message for "no such user" and "wrong password" so the
    # endpoint cannot be used to enumerate registered emails.
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


def _token_for(user: User) -> Token:
    return Token(
        access_token=create_access_token(user.id),
        token_type="bearer",
        expires_in=token_lifetime_seconds(),
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
def register(payload: UserCreate, db: DbSession) -> User:
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        extra_skills=[],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token, summary="Log in with a JSON body")
def login(payload: LoginRequest, db: DbSession) -> Token:
    user = _authenticate(db, payload.email, payload.password)
    return _token_for(user)


@router.post(
    "/token",
    response_model=Token,
    summary="Log in with an OAuth2 password form (used by the /docs Authorize button)",
)
def login_form(
    db: DbSession,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    # OAuth2 spec calls the field "username"; we treat it as the email.
    user = _authenticate(db, form_data.username, form_data.password)
    return _token_for(user)
