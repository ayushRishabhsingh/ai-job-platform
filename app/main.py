"""FastAPI application entry point.

Run it with:
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app.config import BASE_DIR, settings
from app.database import init_db
from app.routers import applications, auth, jobs, recommendations, resumes, system, users

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    init_db()  # dev convenience; use Alembic migrations in production
    logger.info("Database ready: %s", settings.DATABASE_URL.split("://")[0])
    yield
    logger.info("Shutting down")


DESCRIPTION = """
A job recommendation and resume analysis backend.

**Typical flow**

1. `POST /auth/register` then `POST /auth/login` to get a JWT
2. Click **Authorize** above and paste the token
3. `POST /resumes/upload` — the API extracts your skills from the PDF
4. `GET /recommendations` — ranked jobs with a match score and skill gaps
5. `POST /applications` — track what you applied to

**Matching strategies** (`?strategy=`)

| Strategy | How it works | Needs |
|---|---|---|
| `overlap` | matched required skills / required skills, adjusted for experience | nothing |
| `tfidf` | TF-IDF cosine similarity, blended with overlap | scikit-learn |
| `embedding` | sentence-transformer similarity, blended with overlap | sentence-transformers |
"""


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Streamlit runs on a different port, so it is a cross-origin caller.
app.add_middleware(
    CORSMiddleware,
    # The bundled UI is same-origin so it needs nothing here. These entries cover
    # Streamlit and a file:// or live-server copy of the frontend during dev.
    allow_origins=(
        ["*"]
        if settings.DEBUG
        else ["http://localhost:8501", "http://127.0.0.1:8501"]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Log every request and expose how long it took."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-ms"] = f"{elapsed_ms:.1f}"
    logger.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# --- Exception handlers: consistent error shape across the whole API ---
@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    """Flatten Pydantic errors into something a frontend can display."""
    errors = [
        {
            "field": ".".join(str(p) for p in err["loc"][1:]) or err["loc"][0],
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation failed", "errors": errors},
    )


@app.exception_handler(IntegrityError)
async def integrity_handler(request: Request, exc: IntegrityError):
    logger.warning("Integrity error on %s: %s", request.url.path, exc.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "That operation conflicts with existing data"},
    )


# --- Routers ---
app.include_router(system.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(jobs.router)
app.include_router(recommendations.router)  # owns /jobs/{id}/skill-gap
app.include_router(resumes.router)
app.include_router(applications.router)


# --- Web UI ---
# Serving the single-page frontend from the API itself means it is same-origin,
# so there is no CORS to configure and no second server to run.
WEB_DIR = BASE_DIR / "frontend" / "web"
if WEB_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=WEB_DIR, html=True), name="web")
    logger.info("Web UI mounted at /app")
else:  # pragma: no cover
    logger.warning("No web UI found at %s — /app will 404", WEB_DIR)


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    """Send browsers to the UI; /api-index still returns the JSON index."""
    if WEB_DIR.is_dir():
        return RedirectResponse(url="/app/")
    return RedirectResponse(url="/docs")


@app.get("/api-index", tags=["system"], summary="API index")
def root() -> dict:
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "ui": "/app",
        "docs": "/docs",
        "health": "/health",
        "resources": [
            "/auth",
            "/users/me",
            "/jobs",
            "/resumes",
            "/recommendations",
            "/applications",
        ],
    }
