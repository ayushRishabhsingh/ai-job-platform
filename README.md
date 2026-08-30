https://ai-job-platform-api-40og.onrender.com/app/
# AI Job Recommendation & Resume Analyzer API

A production-shaped FastAPI backend that parses resumes, extracts skills, and ranks jobs
against them with an explainable match score — plus a Streamlit frontend that talks to it
purely over REST.

Built as a portfolio project to demonstrate REST API design, PostgreSQL relationships, JWT
auth, file handling, and ML inference in one coherent system.

```
┌─────────────────┐
│    Streamlit    │  frontend/streamlit_app.py — no business logic, HTTP only
│    Frontend     │
└────────┬────────┘
         │ HTTP / REST
         ▼
┌─────────────────┐
│     FastAPI     │  28 endpoints across 6 resources
│   REST Backend  │
└────────┬────────┘
         │
   ┌─────┴──────────────┬─────────────────┐
   ▼                    ▼                 ▼
Auth Service       Job Service      Resume Service
   │                    │                 │
   ▼                    ▼                 ▼
JWT / bcrypt      Recommendation     PDF Parser
                    Engine               │
                       │                 ▼
                       │            Skill Extractor
                       └────────┬────────┘
                                ▼
                          PostgreSQL
                        (or SQLite, zero setup)
```

---

## Status

| | |
|---|---|
| Endpoints | **28** |
| Frontends | 2 — single-file web app + Streamlit |
| Unit + integration tests | **101 passing** |
| Live end-to-end checks | **47 passing** |
| Skill taxonomy | 112 skills with aliases |
| Seeded jobs | 25 across 11 companies |
| Match strategies | 3 (`overlap`, `tfidf`, `embedding`) |

---

## The interface

The web app is one HTML file with no build step, no framework and no dependencies. FastAPI
mounts it as static files, which means it is same-origin with the API — no CORS config, no
second process, no `npm install`.

Its organising idea is the **coverage strip**. Rather than showing a match as one big
percentage, each job renders as a row of cells — one per required skill, solid if you have it
and hollow if you don't:

```
Machine Learning Engineer · Vantage AI
┌────────┬────────┬────────┬╌╌╌╌╌╌╌╌┬╌╌╌╌╌╌╌╌┬╌╌╌╌╌╌╌╌┐
│ Python │  AWS   │ Docker ┊PyTorch ┊  K8s   ┊ MLOps  ┊
└────────┴────────┴────────┴╌╌╌╌╌╌╌╌┴╌╌╌╌╌╌╌╌┴╌╌╌╌╌╌╌╌┘
 3 of 6 skills                              48% match
```

The reasoning: job requirements come in small integers. "You have 3 of 5" is a fact a person
can act on; "60%" is a number that hides its own arithmetic. The percentage is still there,
set small in monospace, because it is what the API sorts by — but the strip is what you read
first, and the missing cells are the actual to-do list.

Four screens: **Matches** (ranked, with strategy switching and an expandable "why this
score"), **All jobs** (search and filter, with your own skills highlighted against each
posting), **Tracker** (six-stage pipeline board), and **Profile** (drag-and-drop resume
upload, extracted skills, preferences).

---

## Quick start

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure (optional — SQLite works with no .env at all)
cp .env.example .env

# 3. Seed 25 jobs and a demo account
python -m scripts.seed

# 4. Run
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000** — the web app is served by the API itself, so there is no
second server to start and no CORS to configure. Log in as `demo@example.com` / `demo12345`.

| Address | What it is |
|---|---|
| `/` | The web app (`frontend/web/index.html`) |
| `/docs` | Interactive OpenAPI docs — every endpoint, testable in the browser |
| `/health` | Status probe |

There is also a Streamlit version of the frontend, if you prefer it:

```bash
streamlit run frontend/streamlit_app.py     # http://localhost:8501
```

### Or the whole stack in Docker

```bash
docker compose up --build
```

That brings up PostgreSQL 16, the API (seeded automatically), and the Streamlit UI.

---

## Try it from the command line

```bash
# Register and log in
curl -X POST localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"password123"}'

TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"password123"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# Upload a resume — skills are extracted from the PDF
curl -X POST localhost:8000/resumes/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F 'file=@/path/to/your_resume.pdf'

# Get ranked recommendations
curl "localhost:8000/recommendations?strategy=overlap&limit=5" \
  -H "Authorization: Bearer $TOKEN"

# Why did job 3 score what it scored?
curl localhost:8000/jobs/3/skill-gap -H "Authorization: Bearer $TOKEN"
```

---

## API reference

### Auth
| Method | Path | Notes |
|---|---|---|
| `POST` | `/auth/register` | 409 on duplicate email |
| `POST` | `/auth/login` | JSON body → JWT |
| `POST` | `/auth/token` | OAuth2 form, powers the `/docs` Authorize button |

### Users
| Method | Path | Notes |
|---|---|---|
| `GET` | `/users/me` | Profile + derived `all_skills` |
| `PATCH` | `/users/me` | Partial update of preferences |
| `DELETE` | `/users/me` | Cascades to resumes and applications |

### Jobs
| Method | Path | Notes |
|---|---|---|
| `GET` | `/jobs` | Filter, sort, paginate — see below |
| `POST` | `/jobs` | Auth required |
| `GET` | `/jobs/{id}` | Public |
| `PUT` | `/jobs/{id}` | Owner or admin only |
| `DELETE` | `/jobs/{id}` | Owner or admin only |

Query parameters on `GET /jobs`:

```
?q=backend                 free text over title, company, description
&location=bangalore        case-insensitive partial match
&company=zeta
&skill=Python&skill=AWS    repeatable, AND-matched
&min_experience=0&max_experience=2
&employment_type=Internship
&is_active=true
&sort_by=salary            created_at | title | company | experience | salary
&order=desc
&page=1&limit=20
```

Every list endpoint returns the same envelope:

```json
{ "items": [...], "total": 25, "page": 1, "limit": 20, "pages": 2 }
```

### Resumes
| Method | Path | Notes |
|---|---|---|
| `POST` | `/resumes/upload` | PDF / DOCX / TXT, 5 MB cap, streamed to disk |
| `GET` | `/resumes` | Paginated |
| `GET` | `/resumes/{id}` | `?include_text=true` for the raw text |
| `POST` | `/resumes/{id}/activate` | Only one active resume per user |
| `PATCH` | `/resumes/{id}/skills` | `{"add": [...], "remove": [...]}` |
| `DELETE` | `/resumes/{id}` | Removes the file from disk too |

### Recommendations
| Method | Path | Notes |
|---|---|---|
| `GET` | `/recommendations` | `?strategy=&limit=&min_score=&location=&max_experience=` |
| `GET` | `/jobs/{id}/skill-gap` | Match score, matched/missing skills, advice |

### Applications
| Method | Path | Notes |
|---|---|---|
| `POST` | `/applications` | 409 if already tracking that job |
| `GET` | `/applications` | `?status=&sort_by=&order=` |
| `GET` | `/applications/stats` | Funnel counts + response rate |
| `GET` | `/applications/{id}` | |
| `PUT` | `/applications/{id}` | Advance status, edit notes |
| `DELETE` | `/applications/{id}` | |

### System
| Method | Path | Notes |
|---|---|---|
| `GET` | `/health` | Actually queries the DB; reports available strategies |
| `GET` | `/skills` | Browse the taxonomy — `?q=` for autocomplete |

---

## How the matching works

Three strategies behind one interface, selected per request with `?strategy=`.

### v1 — `overlap` (default)

```
score = matched required skills / total required skills
```

Then adjusted for the experience gap: being **under**-qualified costs 5 points per missing
year (capped at 25), being **over**-qualified costs 1 point per year (capped at 5). That
asymmetry mirrors how screening actually works.

This is the default on purpose. It is instant, needs no model, and is fully explainable —
the API can always tell the user *which* skills matched and which did not.

### v2 — `tfidf`

TF-IDF vectors over the job corpus, cosine similarity against the resume text. The
vocabulary is fitted **once per request batch**, not once per job.

### v3 — `embedding`

Sentence-transformer embeddings, cosine similarity. Lazily loaded and cached; if
`sentence-transformers` is not installed the endpoint returns a clear `503` pointing at
`tfidf` instead, rather than crashing.

### Blending

Both semantic strategies blend back with the overlap score at **60/40** in favour of
overlap:

```python
combined = overlap_score * 0.6 + semantic_score * 0.4
```

Two reasons. First, a semantic model will happily score a frontend resume at 60% for a
backend role because both documents say "developer" — skill overlap is the sanity check.
Second, the matched/missing skill lists survive the blend, so the score stays explainable
no matter which strategy produced it.

### Skill extraction

Rule-based: a 112-entry taxonomy mapping canonical names to surface forms
(`sklearn` → `Scikit-learn`, `k8s` → `Kubernetes`, `postgres` → `PostgreSQL`), matched with
word-boundary regex. Skills declared in an explicit `SKILLS` section outrank skills merely
mentioned in prose.

Two non-obvious bugs worth knowing about, both fixed and covered by tests:

- `\b` does not work next to `+` or `#`, so a naive matcher finds **C** inside **C++**.
  The patterns use lookarounds that also reject `+` and `#`.
- Two-character aliases match inside longer words — `ml` inside `html`. Aliases of ≤2
  characters are matched case-sensitively in upper case only, so `ML` counts and `html`
  does not.

Ambiguous bare tokens (`r`, `go`) are never matched alone; the longer aliases
(`r programming`, `golang`) catch the real thing without the false positives.

---

## Data model

```
User
 ├── Resume        (1:N, cascade delete; exactly one is_active)
 ├── Application   (1:N, cascade delete)
 │    └── Job      (N:1)
 └── Job           (1:N as poster, SET NULL on delete)
```

Details that matter:

- `UNIQUE (user_id, job_id)` on `applications` — you cannot track the same job twice
- `match_score_at_apply` snapshots the score at save time, so editing your resume later
  does not rewrite history
- Skills live in JSON array columns, filterable on both SQLite and PostgreSQL via a text
  cast; with Postgres only you would switch to native JSONB operators, which are indexable
- `selectinload` on the applications list kills the N+1 on the nested job

---

## Testing

```bash
pytest                                    # 101 tests
pytest tests/test_recommendations.py -v   # one file
pytest --cov=app                          # with coverage (pip install pytest-cov)
```

Each test gets a fresh in-memory SQLite database via a `StaticPool`, so tests are isolated
and order-independent. The `resume_pdf_bytes` fixture generates a **real PDF** with
PyMuPDF, so the upload path is tested end to end rather than mocked.

There is also a live smoke test that runs the full user journey over real HTTP:

```bash
uvicorn app.main:app --port 8001 &
python -m scripts.smoke_test          # 47 checks
```

What the tests actually cover, beyond the happy path:

- Login gives the same error for unknown email and wrong password (no account enumeration)
- Reading another user's resume returns **404, not 403** — so IDs are not enumerable
- Extra skills on your resume do not inflate the score; only the job's requirements count
  toward the denominator
- Deleting a job cascades to its applications
- Deleting your account invalidates the token immediately

---

## Project layout

```
ai-job-platform/
├── app/
│   ├── main.py                  app factory, middleware, exception handlers
│   ├── config.py                pydantic-settings
│   ├── database.py              engine, session, Base, get_db
│   ├── models/                  User, Job, Resume, Application
│   ├── schemas/                 26 Pydantic schemas incl. generic Page[T]
│   ├── core/
│   │   ├── security.py          bcrypt + JWT
│   │   └── deps.py              CurrentUser, Pagination, admin guard
│   ├── routers/                 one module per resource
│   ├── services/
│   │   ├── resume_parser.py     PDF/DOCX/TXT → clean text → sections
│   │   ├── skill_extractor.py   taxonomy matching
│   │   └── matcher.py           the three strategies
│   └── data/skills.py           112-skill taxonomy
├── frontend/
│   ├── web/index.html           single-file web app, served at / by FastAPI
│   └── streamlit_app.py         alternative Streamlit UI, HTTP only
├── scripts/
│   ├── seed.py                  25 jobs + demo user
│   └── smoke_test.py            live end-to-end run
├── tests/                       101 tests
├── Dockerfile                   multi-stage, non-root, healthcheck
├── Dockerfile.ui
└── docker-compose.yml           Postgres + API + UI
```

---

## Switching to PostgreSQL

One line in `.env`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/jobsdb
```

Nothing else changes — no model edits, no query rewrites. That is the payoff for going
through SQLAlchemy rather than raw SQL.

For production, replace `init_db()`'s `create_all` with Alembic migrations:

```bash
alembic init alembic
# point alembic/env.py at app.database.Base.metadata
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

---

## Deploying to AWS

```
        ECR  ◄── docker push
         │
         ▼
        ECS (Fargate)  ──►  RDS (PostgreSQL)
         │
         ▼
   Application Load Balancer  ──►  users
```

```bash
# Build and push
aws ecr create-repository --repository-name ai-job-api
docker build -t ai-job-api .
docker tag ai-job-api:latest <acct>.dkr.ecr.<region>.amazonaws.com/ai-job-api:latest
docker push <acct>.dkr.ecr.<region>.amazonaws.com/ai-job-api:latest
```

Checklist before you point real traffic at it:

- [ ] `SECRET_KEY` from AWS Secrets Manager, never baked into the image
- [ ] `DEBUG=false`
- [ ] Alembic migrations run as an ECS task, not on app startup
- [ ] Resume uploads to **S3**, not the container filesystem — Fargate storage is ephemeral
- [ ] RDS in a private subnet; only the ECS security group may reach 5432
- [ ] ALB health check → `/health` (it queries the database, so it fails honestly)
- [ ] Tighten CORS `allow_origins` to the real frontend domain
- [ ] Rate limiting on `/auth/login` and `/resumes/upload`

---

## Build phases

| Phase | Scope | Status |
|---|---|---|
| 1 | REST fundamentals — `/jobs` CRUD, query params, status codes | ✅ |
| 2 | PostgreSQL + SQLAlchemy models and relationships | ✅ |
| 3 | JWT auth, password hashing, protected routes | ✅ |
| 4 | Resume upload → PDF parse → skill extraction | ✅ |
| 5 | Matching: overlap → TF-IDF → embeddings | ✅ |
| 6 | Application tracking with real relationships | ✅ |
| 7 | Docker, Compose, logging, error handling, tests | ✅ |
| 8 | AWS deployment (ECR → ECS → RDS + ALB) | Documented, not provisioned |

### Where to take it next

- **S3 for uploads** — the one change genuinely required before deploying to Fargate
- **Alembic** — the moment the schema changes after you have data you care about
- **Background parsing** — move resume extraction to Celery or a FastAPI `BackgroundTask`
  so upload returns immediately on large files
- **Caching** — recommendations recompute from scratch each call; Redis keyed on
  `(user_id, resume_updated_at, strategy)` is the obvious win
- **Precomputed embeddings** — store a job's vector on write, not per request; this is what
  makes the `embedding` strategy viable at scale
- **Rate limiting** — `slowapi` on the auth and upload endpoints

---

## Notes on a few design decisions

**Why `overlap` is the default rather than embeddings.** An explainable 60% beats an
unexplainable 74%. Users trust a score they can interrogate, and "you're missing Kubernetes
and PyTorch" is more actionable than a similarity number. The semantic strategies are there
for when the resume and the job description use different vocabulary for the same thing.

**Why the score is snapshotted on the application row.** Without it, your tracker rewrites
its own history every time you edit your resume — last month's 40% match silently becomes
today's 85%, and the record becomes useless for spotting patterns.

**Why 404 instead of 403 for other users' resumes.** A 403 confirms the resource exists,
which turns sequential IDs into an enumeration oracle. 404 says nothing.

**Why the health check queries the database.** A health endpoint that only returns `{"status":
"ok"}` tells a load balancer nothing — the process being alive is not the same as the
service being able to serve requests.
