"""Shared test fixtures.

Every test gets a fresh SQLite database file, so tests never see each other's
rows and can run in any order.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Job


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """In-memory SQLite shared across connections for the duration of one test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # keeps the same in-memory DB across sessions
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient wired to the test database."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ----------------------------------------------------------------------
# Auth helpers
# ----------------------------------------------------------------------
USER_EMAIL = "test@example.com"
USER_PASSWORD = "testpass123"


@pytest.fixture
def registered_user(client: TestClient) -> dict:
    response = client.post(
        "/auth/register",
        json={"email": USER_EMAIL, "password": USER_PASSWORD, "full_name": "Test User"},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def auth_headers(client: TestClient, registered_user: dict) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def second_user_headers(client: TestClient) -> dict[str, str]:
    """A different account, for testing ownership rules."""
    client.post("/auth/register", json={"email": "other@example.com", "password": "otherpass123"})
    response = client.post(
        "/auth/login", json={"email": "other@example.com", "password": "otherpass123"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ----------------------------------------------------------------------
# Data helpers
# ----------------------------------------------------------------------
SAMPLE_JOB = {
    "title": "Backend Engineer",
    "company": "Acme Corp",
    "location": "Bangalore",
    "description": "Build APIs with Python and FastAPI.",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
    "experience_required": 1,
    "salary_min": 1000000,
    "salary_max": 1500000,
}


@pytest.fixture
def sample_job(db_session: Session) -> Job:
    job = Job(**SAMPLE_JOB)
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def job_pool(db_session: Session) -> list[Job]:
    """A small, deliberately varied set of jobs for ranking tests."""
    jobs = [
        Job(
            title="Python Backend Engineer",
            company="Alpha",
            location="Bangalore",
            description="Python FastAPI PostgreSQL Docker AWS backend services",
            skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
            experience_required=1,
        ),
        Job(
            title="Frontend Developer",
            company="Beta",
            location="Pune",
            description="React TypeScript CSS design systems",
            skills=["React", "TypeScript", "CSS", "HTML"],
            experience_required=2,
        ),
        Job(
            title="ML Engineer",
            company="Gamma",
            location="Bangalore",
            description="PyTorch Kubernetes model serving",
            skills=["Python", "PyTorch", "AWS", "Docker", "Kubernetes"],
            experience_required=3,
        ),
    ]
    db_session.add_all(jobs)
    db_session.commit()
    for job in jobs:
        db_session.refresh(job)
    return jobs


@pytest.fixture
def resume_pdf_bytes() -> bytes:
    """Generate a real, single-page PDF containing a resume-like skills block."""
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    lines = [
        "Test Candidate",
        "",
        "TECHNICAL SKILLS",
        "Python, C++, FastAPI, PostgreSQL, Docker, AWS, SQL, Git",
        "",
        "EXPERIENCE",
        "Built REST APIs with FastAPI and deployed them with Docker on AWS.",
        "Used pandas and NumPy for data analysis and Power BI for dashboards.",
    ]
    page.insert_text((60, 80), "\n".join(lines), fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data
