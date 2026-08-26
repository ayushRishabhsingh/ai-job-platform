"""Reusable FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_access_token
from app.database import get_db
from app.models import User

# tokenUrl makes the "Authorize" button work in /docs
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    db: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User:
    """Resolve the Bearer token into a User, or raise 401."""
    if not token:
        raise CREDENTIALS_EXCEPTION

    payload = decode_access_token(token)
    if payload is None:
        raise CREDENTIALS_EXCEPTION

    subject = payload.get("sub")
    if subject is None or not str(subject).isdigit():
        raise CREDENTIALS_EXCEPTION

    user = db.get(User, int(subject))
    if user is None:
        raise CREDENTIALS_EXCEPTION
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Guard for endpoints that mutate shared data (e.g. deleting any job)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


def get_optional_user(
    db: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User | None:
    """Like get_current_user but returns None instead of raising."""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    subject = payload.get("sub")
    if not subject or not str(subject).isdigit():
        return None
    return db.get(User, int(subject))


class PaginationParams:
    """?page=1&limit=20 — shared by every list endpoint."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="1-indexed page number")] = 1,
        limit: Annotated[int | None, Query(ge=1, le=100, description="Rows per page")] = None,
    ):
        self.page = page
        self.limit = limit or settings.DEFAULT_PAGE_SIZE
        self.offset = (self.page - 1) * self.limit


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
Pagination = Annotated[PaginationParams, Depends()]
