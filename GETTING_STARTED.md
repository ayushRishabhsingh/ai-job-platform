# Getting Started — Read This First

If you tried opening `http://127.0.0.1:8000/docs` and got **"This site can't be reached"**,
nothing is broken. This guide explains why, and gets you running in about five minutes.

---

## First: what `127.0.0.1` actually is

`127.0.0.1` is **not a website on the internet.** It is a reserved address that always means
*"this computer, right here."* Its nickname is **localhost**.

- `google.com` → a computer in a Google data centre
- `127.0.0.1` → **your own laptop**

So `http://127.0.0.1:8000/docs` means: *"connect to a program running on my own machine,
on port 8000, and open the `/docs` page."*

Right now there is no such program running. That is why the browser says it can't reach it.
Once you start the API on your laptop, **your laptop becomes the server** and that address
starts working — but only in your own browser, on your own machine.

Two things this means:

- **Nobody else can open that link.** Not your friends, not on your phone. It is local only.
  (Deploying to AWS is what makes it public — that is Phase 8 in the README.)
- **The page disappears when you stop the program.** Close the terminal, and the URL goes
  dead again. That is normal.

The `:8000` part is the **port** — like a door number on the building. The API listens on
door 8000. Streamlit listens on 8501.

---

## What you need first

**Python 3.11 or newer.** Check by opening a terminal and typing:

```bash
python --version
```

If that says `Python 3.11.x` or higher, you're set. If it says "command not found" or shows
2.x, try `python3 --version` instead. If neither works, install Python from
[python.org/downloads](https://www.python.org/downloads/) — and on Windows, **tick the box
that says "Add Python to PATH"** during installation. That checkbox causes most of the
"command not found" problems people hit later.

**How to open a terminal:**

| OS | How |
|---|---|
| Windows | Press `Win`, type `powershell`, press Enter |
| macOS | Press `Cmd+Space`, type `terminal`, press Enter |
| Linux | `Ctrl+Alt+T` |

Below, wherever you see `python`, use `python3` instead if that's what worked for you.

---

## The five steps

### 1. Unzip the project somewhere you can find

Unzip `ai-job-platform.zip` — Desktop or Documents is fine. You should end up with a folder
called `ai-job-platform` containing `README.md`, an `app` folder, and others.

### 2. Point your terminal at that folder

This is the step people skip, and then nothing works. The terminal has to be *inside* the
project folder.

```bash
cd path/to/ai-job-platform
```

**Easiest way to get the path right:** type `cd ` (with a space), then drag the
`ai-job-platform` folder from your file manager into the terminal window. It pastes the path
for you. Press Enter.

Confirm you're in the right place:

```bash
ls          # macOS/Linux
dir         # Windows
```

You should see `README.md`, `requirements.txt`, and an `app` folder listed. If you don't,
you're in the wrong directory — `cd` again.

### 3. Install the packages

```bash
python -m venv .venv
```

That creates an isolated environment so this project's packages don't collide with anything
else on your system. Now activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows Command Prompt
.venv\Scripts\activate.bat
```

Your prompt should now start with `(.venv)`. That's how you know it worked.

> **Windows PowerShell blocking the activate script?** If you see "running scripts is
> disabled on this system," run this once, then try activating again:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

Now install:

```bash
pip install -r requirements.txt
```

This downloads FastAPI, SQLAlchemy, scikit-learn and the rest. **Expect 1–3 minutes** and a
wall of scrolling text — that's normal. It's done when your prompt comes back.

### 4. Put some jobs in the database

```bash
python -m scripts.seed
```

You should see:

```
Created demo user: demo@example.com / demo12345
Inserted 25 jobs.
Created 2 example applications.

Done. 25 jobs in the database.
```

### 5. Start the server

```bash
uvicorn app.main:app --reload
```

Now you'll see something like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

**That line is your signal.** The server is now running. *Now* open your browser and go to:

**http://127.0.0.1:8000**

The web app loads — log in with `demo@example.com` / `demo12345`.

That address also gives you two other views of the same thing:

| Address | What it is |
|---|---|
| `http://127.0.0.1:8000` | **The web app.** Start here. |
| `http://127.0.0.1:8000/docs` | Interactive API docs — every endpoint, testable in the browser |
| `http://127.0.0.1:8000/health` | Plain JSON status check |

> **Leave that terminal open.** The server runs *in* that window. Closing it, or pressing
> `Ctrl+C`, stops the server and the URL goes dead. To use your terminal for something else,
> open a second window.

---

## Using the /docs page

This page is generated automatically by FastAPI from the code. Every endpoint is listed and
clickable — you can test the entire API from your browser without writing any code.

### Log in first

Most endpoints need you to be logged in.

1. Click the green **Authorize** button (top right)
2. Username: `demo@example.com` — Password: `demo12345`
3. Click **Authorize**, then **Close**

The padlock icons across the page switch to locked, meaning your requests are now
authenticated.

### Make your first request

1. Find **`GET /jobs`** and click the row to expand it
2. Click **Try it out** (right side)
3. Click the blue **Execute** button
4. Scroll down to **Response body** — you'll see 25 jobs as JSON

Now try the interesting one:

1. Expand **`GET /recommendations`**
2. **Try it out** → **Execute**
3. You get ranked jobs with a `match_score`, plus `matched_skills` and `missing_skills` for
   each one

The demo account has Python, FastAPI, PostgreSQL, Docker, AWS and Machine Learning on it, so
backend and ML roles should score high and the frontend role should score low.

### Worth trying

| Endpoint | What to do |
|---|---|
| `POST /resumes/upload` | Upload your **real resume PDF** and see which skills it finds |
| `GET /jobs/{job_id}/skill-gap` | Enter `2` as the job_id — shows what you'd need to learn |
| `GET /jobs` | Set `location` to `Bangalore` and `skill` to `Python` |
| `POST /applications` | Enter `{"job_id": 3, "status": "Applied"}` to track a job |
| `GET /applications/stats` | Your funnel: counts per stage and response rate |

---

## The visual interface (optional but nicer)

The `/docs` page is a developer tool. There's also a real UI.

**Keep the API terminal running.** Open a *second* terminal, then:

```bash
cd path/to/ai-job-platform

# activate the environment again in this new window
source .venv/bin/activate          # macOS/Linux
.venv\Scripts\Activate.ps1         # Windows

streamlit run frontend/streamlit_app.py
```

Your browser opens `http://localhost:8501` automatically. Log in with the same demo
credentials. You get four pages: Recommendations (with match-score bars), Browse jobs,
Tracker, and Profile (where you upload your resume).

Two terminals, two programs: the API on port 8000, the UI on port 8501. The UI talks to the
API over HTTP — it holds no logic of its own.

---

## When something goes wrong

**`can't reach this site` / `connection refused` in the browser**
The server isn't running. Go back to your terminal — is `Uvicorn running on...` still
showing? If the terminal is back at a normal prompt, the server stopped. Run step 5 again.

**`uvicorn: command not found`**
The virtual environment isn't active. Does your prompt show `(.venv)`? If not, re-run the
activate command from step 3. If it is active, run `pip install -r requirements.txt` again.

**`ModuleNotFoundError: No module named 'app'`**
You're in the wrong folder. Run `ls` (or `dir`) — you must see the `app` folder. If you see
`main.py` and `config.py` instead, you went one level too deep: `cd ..`

**`ModuleNotFoundError: No module named 'fastapi'`**
Packages didn't install, or the environment isn't active. Activate, then reinstall.

**`Address already in use` / `port 8000 is in use`**
Something else has that port — possibly an old server you forgot about. Use a different
door:
```bash
uvicorn app.main:app --reload --port 8080
```
Then browse to `http://127.0.0.1:8080/docs` instead.

**`{"detail":"Not authenticated"}` in a response**
Click **Authorize** and log in. This appears after your token expires too — just
re-authorize.

**`400: No skills on file` from `/recommendations`**
The account has no skills. Either upload a resume via `POST /resumes/upload`, or add them
with `PATCH /users/me`:
```json
{"extra_skills": ["Python", "FastAPI", "Docker"], "years_experience": 1}
```

**`503` from `?strategy=embedding`**
That's expected. The embedding model is a ~500 MB download so it's not installed by default.
Use `?strategy=overlap` or `?strategy=tfidf`. To enable it:
`pip install sentence-transformers`

**Everything is broken and I want to start over**
```bash
rm jobs.db                    # Windows: del jobs.db
python -m scripts.seed
```
That wipes the database and reseeds it. Nothing else is destroyed.

---

## Proving it works, without a browser

Want to confirm the whole system is functioning? With the server running, open a second
terminal (environment activated) and run:

```bash
pytest
```

101 tests. All should pass in about 40 seconds.

```bash
SMOKE_BASE_URL=http://127.0.0.1:8000 python -m scripts.smoke_test
```

47 checks against the live server — register, log in, upload a PDF, get recommendations,
track an application, clean up.

---

## Making it a real website

Everything above runs on your machine only. To give someone else a link, the code has to run
on a computer that's always on and reachable from the internet.

The README has the full AWS path (ECR → ECS → RDS), but the shortest route to a live URL is
a platform-as-a-service host like Render or Railway: connect a GitHub repo, set
`DATABASE_URL` and `SECRET_KEY` as environment variables, and it builds the Dockerfile for
you.

One thing to change before you do: **resume uploads currently write to the local disk**, and
most hosts wipe that on every redeploy. Move uploads to S3 (or the host's object storage)
first. It's the first item in the README's next-steps list.

---

## Quick reference

```bash
# One-time setup
cd path/to/ai-job-platform
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m scripts.seed

# Every time you want to run it
cd path/to/ai-job-platform
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
# then open http://127.0.0.1:8000/docs
```

| Address | What it is | Needs |
|---|---|---|
| `http://127.0.0.1:8000/docs` | Interactive API docs | `uvicorn` running |
| `http://127.0.0.1:8000/health` | Status check — returns JSON | `uvicorn` running |
| `http://localhost:8501` | Streamlit visual UI | `streamlit` running |

Login for both: `demo@example.com` / `demo12345`

> `localhost` and `127.0.0.1` are the same thing. Use whichever you prefer.
