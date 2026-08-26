"""Shared / generic schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Message(BaseModel):
    detail: str


class Page(BaseModel, Generic[T]):
    """Standard pagination envelope returned by every list endpoint."""

    items: list[T]
    total: int = Field(description="Total rows matching the filters, ignoring pagination")
    page: int
    limit: int
    pages: int

    @classmethod
    def build(cls, items: list[T], total: int, page: int, limit: int) -> "Page[T]":
        pages = (total + limit - 1) // limit if limit else 0
        return cls(items=items, total=total, page=page, limit=limit, pages=pages)


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    database: str
    match_strategies: list[str]
