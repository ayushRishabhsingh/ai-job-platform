"""Seed the database with realistic job postings and a demo account.

Usage:
    python -m scripts.seed            # add jobs if the table is empty
    python -m scripts.seed --reset    # drop everything and start clean
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.models import Application, ApplicationStatus, Job, User  # noqa: E402

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo12345"

JOBS: list[dict] = [
    {
        "title": "Backend Engineer (Python)",
        "company": "Zeta Payments",
        "location": "Bangalore",
        "experience_required": 0,
        "employment_type": "Full-time",
        "salary_min": 900000,
        "salary_max": 1400000,
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "REST API", "Git"],
        "description": (
            "Build and maintain payment APIs serving millions of requests a day. "
            "You will own endpoints end to end, write the tests, and deploy them."
        ),
    },
    {
        "title": "Machine Learning Engineer",
        "company": "Vantage AI",
        "location": "Bangalore",
        "experience_required": 2,
        "salary_min": 1800000,
        "salary_max": 2800000,
        "skills": ["Python", "PyTorch", "AWS", "Docker", "Kubernetes", "MLOps", "Machine Learning"],
        "description": (
            "Train and serve recommendation models in production. Ownership of the "
            "full lifecycle: data pipeline, training, evaluation, deployment, monitoring."
        ),
    },
    {
        "title": "AI Engineer — LLM Applications",
        "company": "Corvus Labs",
        "location": "Remote",
        "experience_required": 1,
        "salary_min": 1600000,
        "salary_max": 2400000,
        "skills": [
            "Python",
            "LLMs",
            "RAG",
            "LangChain",
            "Vector Databases",
            "FastAPI",
            "Embeddings",
        ],
        "description": (
            "Ship retrieval-augmented generation features. You will design chunking "
            "and retrieval strategies and evaluate them against real user queries."
        ),
    },
    {
        "title": "Junior Data Analyst",
        "company": "Meridian Retail",
        "location": "Chennai",
        "experience_required": 0,
        "salary_min": 500000,
        "salary_max": 800000,
        "skills": ["SQL", "Excel", "Power BI", "Data Analysis", "Statistics"],
        "description": "Build weekly dashboards for the merchandising team and answer ad-hoc questions.",
    },
    {
        "title": "Data Engineer",
        "company": "Northwind Logistics",
        "location": "Hyderabad",
        "experience_required": 3,
        "salary_min": 1800000,
        "salary_max": 2600000,
        "skills": ["Python", "SQL", "Apache Spark", "Airflow", "AWS", "ETL", "Data Warehousing"],
        "description": "Own the ingestion layer feeding our analytics warehouse. Batch and streaming.",
    },
    {
        "title": "Full Stack Developer",
        "company": "Fable Studios",
        "location": "Pune",
        "experience_required": 2,
        "salary_min": 1200000,
        "salary_max": 1900000,
        "skills": ["TypeScript", "React", "Node.js", "PostgreSQL", "Docker", "REST API"],
        "description": "Build customer-facing product features across the stack in two-week cycles.",
    },
    {
        "title": "Platform / DevOps Engineer",
        "company": "Zeta Payments",
        "location": "Bangalore",
        "experience_required": 3,
        "salary_min": 2000000,
        "salary_max": 3200000,
        "skills": ["Kubernetes", "Terraform", "AWS", "Docker", "CI/CD", "Linux", "Monitoring"],
        "description": "Own the deployment platform: clusters, pipelines, observability, on-call.",
    },
    {
        "title": "NLP Engineer",
        "company": "Lexis Health",
        "location": "Remote",
        "experience_required": 2,
        "salary_min": 1700000,
        "salary_max": 2600000,
        "skills": ["Python", "NLP", "Transformers", "Hugging Face", "PyTorch", "spaCy"],
        "description": "Extract structured clinical data from unstructured physician notes.",
    },
    {
        "title": "Backend Intern",
        "company": "Corvus Labs",
        "location": "Remote",
        "experience_required": 0,
        "employment_type": "Internship",
        "salary_min": 300000,
        "salary_max": 480000,
        "skills": ["Python", "Flask", "SQL", "Git", "REST API"],
        "description": "Six-month internship on the API team. Real tickets, code review, mentorship.",
    },
    {
        "title": "Software Engineer I",
        "company": "Halcyon Systems",
        "location": "Chennai",
        "experience_required": 0,
        "salary_min": 800000,
        "salary_max": 1200000,
        "skills": ["Java", "Spring Boot", "SQL", "Data Structures", "Algorithms", "Git"],
        "description": "Graduate role on the core services team. Strong CS fundamentals expected.",
    },
    {
        "title": "Senior Backend Engineer",
        "company": "Aperture Cloud",
        "location": "Bangalore",
        "experience_required": 5,
        "salary_min": 3200000,
        "salary_max": 5000000,
        "skills": [
            "Python",
            "Go",
            "PostgreSQL",
            "Redis",
            "Kubernetes",
            "System Design",
            "Microservices",
        ],
        "description": "Design and scale multi-tenant services. You will set technical direction.",
    },
    {
        "title": "Analytics Engineer",
        "company": "Meridian Retail",
        "location": "Chennai",
        "experience_required": 2,
        "salary_min": 1300000,
        "salary_max": 2000000,
        "skills": ["SQL", "Python", "Data Warehousing", "ETL", "Power BI", "Statistics"],
        "description": "Model raw event data into trustworthy tables the whole company can query.",
    },
    {
        "title": "Computer Vision Engineer",
        "company": "Orbital Robotics",
        "location": "Pune",
        "experience_required": 3,
        "salary_min": 1900000,
        "salary_max": 2900000,
        "skills": ["Python", "Computer Vision", "OpenCV", "PyTorch", "Deep Learning", "C++"],
        "description": "Perception stack for warehouse robots: detection, tracking, calibration.",
    },
    {
        "title": "Automation Engineer (PLC)",
        "company": "Solaris Manufacturing",
        "location": "Ahmedabad",
        "experience_required": 2,
        "salary_min": 700000,
        "salary_max": 1200000,
        "skills": [
            "PLC Programming",
            "SCADA",
            "Automation",
            "Preventive Maintenance",
            "Root Cause Analysis",
        ],
        "description": "Maintain and improve line automation across a high-volume production floor.",
    },
    {
        "title": "Maintenance Engineer — Process Equipment",
        "company": "Solaris Manufacturing",
        "location": "Jamnagar",
        "experience_required": 1,
        "salary_min": 600000,
        "salary_max": 1100000,
        "skills": [
            "Preventive Maintenance",
            "PLC Programming",
            "Root Cause Analysis",
            "Six Sigma",
            "Excel",
        ],
        "description": "Own uptime on the wet process cluster. RCA, spares planning, shift handover.",
    },
    {
        "title": "Site Reliability Engineer",
        "company": "Aperture Cloud",
        "location": "Remote",
        "experience_required": 4,
        "salary_min": 2600000,
        "salary_max": 4000000,
        "skills": ["Linux", "Kubernetes", "Monitoring", "Python", "Terraform", "CI/CD", "AWS"],
        "description": "Keep the platform up. Error budgets, incident response, automation over toil.",
    },
    {
        "title": "Product Analyst",
        "company": "Fable Studios",
        "location": "Bangalore",
        "experience_required": 1,
        "salary_min": 900000,
        "salary_max": 1500000,
        "skills": ["SQL", "Statistics", "Data Analysis", "Tableau", "Excel"],
        "description": "Own experimentation: design A/B tests, read the results honestly, brief the team.",
    },
    {
        "title": "Backend Engineer (Node.js)",
        "company": "Kettle Commerce",
        "location": "Gurgaon",
        "experience_required": 2,
        "salary_min": 1300000,
        "salary_max": 2000000,
        "skills": ["Node.js", "TypeScript", "Express.js", "MongoDB", "Redis", "REST API", "Docker"],
        "description": "Order and inventory services for a high-traffic marketplace.",
    },
    {
        "title": "MLOps Engineer",
        "company": "Vantage AI",
        "location": "Hyderabad",
        "experience_required": 3,
        "salary_min": 2200000,
        "salary_max": 3400000,
        "skills": [
            "Python",
            "MLOps",
            "Docker",
            "Kubernetes",
            "AWS",
            "CI/CD",
            "Airflow",
            "Monitoring",
        ],
        "description": "Build the paved road that lets data scientists ship models without asking you.",
    },
    {
        "title": "Graduate Engineer Trainee — Software",
        "company": "Halcyon Systems",
        "location": "Chennai",
        "experience_required": 0,
        "employment_type": "Full-time",
        "salary_min": 600000,
        "salary_max": 900000,
        "skills": [
            "C++",
            "Data Structures",
            "Algorithms",
            "Linux",
            "Git",
            "Object-Oriented Programming",
        ],
        "description": "Twelve-month structured training programme, then placement onto a product team.",
    },
    {
        "title": "Search Engineer",
        "company": "Kettle Commerce",
        "location": "Bangalore",
        "experience_required": 3,
        "salary_min": 2000000,
        "salary_max": 3100000,
        "skills": [
            "Elasticsearch",
            "Python",
            "NLP",
            "Embeddings",
            "Vector Databases",
            "Recommendation Systems",
        ],
        "description": "Own relevance for product search: ranking, query understanding, evaluation.",
    },
    {
        "title": "Python Developer (Data)",
        "company": "Northwind Logistics",
        "location": "Chennai",
        "experience_required": 1,
        "salary_min": 800000,
        "salary_max": 1400000,
        "skills": ["Python", "Pandas", "NumPy", "SQL", "Data Analysis", "Testing"],
        "description": "Automate reporting pipelines and clean up the data quality checks around them.",
    },
    {
        "title": "Cloud Engineer",
        "company": "Solaris Manufacturing",
        "location": "Ahmedabad",
        "experience_required": 2,
        "salary_min": 1200000,
        "salary_max": 1800000,
        "skills": ["AWS", "Docker", "Linux", "Terraform", "Python", "Monitoring"],
        "description": "Migrate on-premise plant reporting workloads to AWS and keep them cheap.",
    },
    {
        "title": "Research Engineer — Recommender Systems",
        "company": "Vantage AI",
        "location": "Remote",
        "experience_required": 4,
        "salary_min": 2800000,
        "salary_max": 4500000,
        "skills": [
            "Python",
            "Recommendation Systems",
            "Deep Learning",
            "PyTorch",
            "Feature Engineering",
            "Statistics",
            "Machine Learning",
        ],
        "description": "Move offline metrics that survive contact with an online A/B test.",
    },
    {
        "title": "QA Automation Engineer",
        "company": "Fable Studios",
        "location": "Pune",
        "experience_required": 2,
        "salary_min": 900000,
        "salary_max": 1500000,
        "skills": ["Python", "Testing", "CI/CD", "REST API", "Git", "Docker"],
        "description": "Build the regression suite and make it fast enough that people keep it green.",
    },
]


def seed(reset: bool = False) -> None:
    if reset:
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)

    init_db()
    db = SessionLocal()

    try:
        # --- Demo user ---
        demo = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if demo is None:
            demo = User(
                email=DEMO_EMAIL,
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name="Demo Candidate",
                preferred_location="Bangalore",
                years_experience=1,
                extra_skills=[
                    "Python",
                    "FastAPI",
                    "PostgreSQL",
                    "Docker",
                    "AWS",
                    "Machine Learning",
                ],
            )
            db.add(demo)
            db.commit()
            db.refresh(demo)
            print(f"Created demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        else:
            print(f"Demo user already exists: {DEMO_EMAIL}")

        # --- Jobs ---
        existing = db.scalar(select(func.count()).select_from(Job)) or 0
        if existing:
            print(f"Jobs table already has {existing} rows — skipping job seed.")
        else:
            for payload in JOBS:
                db.add(Job(**payload))
            db.commit()
            print(f"Inserted {len(JOBS)} jobs.")

        # --- A couple of tracked applications, so /applications/stats is not empty ---
        if not db.scalar(select(func.count()).select_from(Application)):
            first_two = list(db.scalars(select(Job).limit(2)))
            states = [ApplicationStatus.APPLIED, ApplicationStatus.INTERVIEW]
            for job, state in zip(first_two, states[: len(first_two)], strict=True):
                db.add(
                    Application(
                        user_id=demo.id,
                        job_id=job.id,
                        status=state,
                        notes=f"Seeded example: {state.value}",
                    )
                )
            db.commit()
            print(f"Created {len(first_two)} example applications.")

        total_jobs = db.scalar(select(func.count()).select_from(Job))
        print(f"\nDone. {total_jobs} jobs in the database.")
        print("Start the API with:  uvicorn app.main:app --reload")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the job database")
    parser.add_argument("--reset", action="store_true", help="Drop all tables first")
    args = parser.parse_args()
    seed(reset=args.reset)
