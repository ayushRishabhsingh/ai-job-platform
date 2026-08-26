"""API routers, one module per resource."""

from app.routers import applications, auth, jobs, recommendations, resumes, system, users

__all__ = ["applications", "auth", "jobs", "recommendations", "resumes", "system", "users"]
