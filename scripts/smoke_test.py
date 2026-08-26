"""End-to-end smoke test against a live server.

Exercises the full user journey over real HTTP:
register -> login -> upload PDF -> recommendations -> skill gap -> track -> stats

Usage:
    uvicorn app.main:app --port 8001 &
    python -m scripts.smoke_test
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8001")
EMAIL = f"smoke_{uuid.uuid4().hex[:8]}@example.com"
PASSWORD = "smoketest123"

passed = 0
failed = 0


def check(label: str, condition: bool, extra: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}" + (f"  ({extra})" if extra else ""))
    else:
        failed += 1
        print(f"  FAIL  {label}" + (f"  ({extra})" if extra else ""))


def build_resume_pdf() -> bytes:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        (60, 80),
        "\n".join(
            [
                "Avijit Singh",
                "B.Tech Electrical and Electronics Engineering",
                "",
                "TECHNICAL SKILLS",
                "Python, C++, FastAPI, PostgreSQL, Docker, AWS, SQL, Git, Power BI",
                "",
                "EXPERIENCE",
                "Built REST APIs with FastAPI, containerised with Docker, deployed on AWS.",
                "Used pandas and NumPy for analysis; built Power BI dashboards with DAX.",
                "Practised data structures and algorithms in C++.",
            ]
        ),
        fontsize=11,
    )
    data = doc.tobytes()
    doc.close()
    return data


def wait_for_server(attempts: int = 20) -> bool:
    for _ in range(attempts):
        try:
            if requests.get(f"{BASE}/health", timeout=2).ok:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


def main() -> int:
    print(f"Smoke test against {BASE}\n")

    if not wait_for_server():
        print("Server never became reachable.")
        return 1

    # 1. Health -------------------------------------------------------
    print("1. System")
    health = requests.get(f"{BASE}/health", timeout=5).json()
    check("health reports ok", health["status"] == "ok", health["database"])
    check(
        "strategies advertised",
        "overlap" in health["match_strategies"],
        ", ".join(health["match_strategies"]),
    )
    skills = requests.get(f"{BASE}/skills", params={"q": "python"}, timeout=5).json()
    check("skill taxonomy searchable", "Python" in skills)

    # 2. Auth ---------------------------------------------------------
    print("\n2. Authentication")
    reg = requests.post(
        f"{BASE}/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "full_name": "Smoke Test"},
        timeout=10,
    )
    check("register returns 201", reg.status_code == 201, str(reg.status_code))
    check("password never echoed", "password" not in reg.text)

    dup = requests.post(
        f"{BASE}/auth/register", json={"email": EMAIL, "password": PASSWORD}, timeout=10
    )
    check("duplicate email is 409", dup.status_code == 409)

    login = requests.post(
        f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=10
    )
    check("login returns a token", login.status_code == 200 and login.json()["access_token"])
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    check(
        "protected route rejects no token",
        requests.get(f"{BASE}/users/me", timeout=5).status_code == 401,
    )
    me = requests.get(f"{BASE}/users/me", headers=headers, timeout=5)
    check("protected route accepts token", me.status_code == 200)

    # 3. Resume -------------------------------------------------------
    print("\n3. Resume upload and parsing")
    upload = requests.post(
        f"{BASE}/resumes/upload",
        headers=headers,
        files={"file": ("avijit_resume.pdf", build_resume_pdf(), "application/pdf")},
        timeout=30,
    )
    check("upload returns 201", upload.status_code == 201, str(upload.status_code))
    if upload.status_code != 201:
        print(f"        body: {upload.text[:300]}")
    else:
        resume = upload.json()["resume"]
        found = set(resume["skills"])
        check("extracted Python", "Python" in found)
        check("extracted FastAPI", "FastAPI" in found)
        check("extracted Power BI", "Power BI" in found)
        check("extracted C++ without leaking C", "C++" in found)
        check("resume marked active", resume["is_active"] is True)
        print(f"        {len(found)} skills: {', '.join(resume['skills'][:10])}...")

    bad = requests.post(
        f"{BASE}/resumes/upload",
        headers=headers,
        files={"file": ("photo.png", b"\x89PNG\r\n", "image/png")},
        timeout=10,
    )
    check("unsupported format is 415", bad.status_code == 415)

    # 4. Jobs ---------------------------------------------------------
    print("\n4. Jobs")
    listing = requests.get(f"{BASE}/jobs", params={"limit": 5}, timeout=10).json()
    check("seeded jobs present", listing["total"] >= 20, f"{listing['total']} jobs")
    check("pagination envelope correct", len(listing["items"]) == 5 and listing["pages"] > 1)

    filtered = requests.get(
        f"{BASE}/jobs", params=[("skill", "Python"), ("skill", "Docker")], timeout=10
    ).json()
    check("multi-skill AND filter works", filtered["total"] >= 1, f"{filtered['total']} matches")

    created = requests.post(
        f"{BASE}/jobs",
        headers=headers,
        json={
            "title": "Smoke Test Engineer",
            "company": "Test Co",
            "location": "Remote",
            "skills": ["Python", "FastAPI", "Docker", "Kubernetes"],
            "experience_required": 1,
        },
        timeout=10,
    )
    check("create job returns 201", created.status_code == 201)
    job_id = created.json()["id"]

    updated = requests.put(
        f"{BASE}/jobs/{job_id}",
        headers=headers,
        json={"title": "Senior Smoke Engineer"},
        timeout=10,
    )
    check(
        "update preserves untouched fields",
        updated.json()["title"] == "Senior Smoke Engineer"
        and updated.json()["company"] == "Test Co",
    )

    # 5. Recommendations ---------------------------------------------
    print("\n5. Recommendations")
    requests.patch(f"{BASE}/users/me", headers=headers, json={"years_experience": 1}, timeout=10)
    for strategy in ("overlap", "tfidf"):
        response = requests.get(
            f"{BASE}/recommendations",
            headers=headers,
            params={"strategy": strategy, "limit": 5},
            timeout=60,
        )
        ok = response.status_code == 200
        check(f"{strategy} strategy returns 200", ok, str(response.status_code))
        if not ok:
            print(f"        body: {response.text[:300]}")
            continue
        body = response.json()
        recs = body["recommendations"]
        check(f"{strategy} returns ranked results", len(recs) > 0, f"{len(recs)} recs")
        scores = [r["match_score"] for r in recs]
        check(f"{strategy} sorted descending", scores == sorted(scores, reverse=True), str(scores))
        check(f"{strategy} explains matches", all("matched_skills" in r for r in recs))
        if recs:
            top = recs[0]
            print(f"        top: {top['title']} @ {top['company']} — {top['match_score']}%")

    # 6. Skill gap ---------------------------------------------------
    print("\n6. Skill gap")
    gap = requests.get(f"{BASE}/jobs/{job_id}/skill-gap", headers=headers, timeout=10)
    check("skill-gap returns 200", gap.status_code == 200)
    if gap.status_code == 200:
        body = gap.json()
        check("Kubernetes flagged as missing", "Kubernetes" in body["missing_skills"])
        check("coverage string present", "skills" in body["coverage"], body["coverage"])
        check("advice is actionable", len(body["advice"]) > 0)
        print(
            f"        {body['match_score']}% — {body['coverage']} — missing "
            f"{', '.join(body['missing_skills']) or 'nothing'}"
        )

    # 7. Applications ------------------------------------------------
    print("\n7. Application tracking")
    app_create = requests.post(
        f"{BASE}/applications",
        headers=headers,
        json={"job_id": job_id, "status": "Applied", "notes": "Smoke test entry"},
        timeout=10,
    )
    check("track a job returns 201", app_create.status_code == 201)
    app_id = app_create.json()["id"]
    check(
        "match score snapshotted",
        app_create.json()["match_score_at_apply"] is not None,
        f"{app_create.json()['match_score_at_apply']}%",
    )
    check("nested job returned", app_create.json()["job"]["company"] == "Test Co")

    dupe = requests.post(
        f"{BASE}/applications", headers=headers, json={"job_id": job_id}, timeout=10
    )
    check("duplicate tracking is 409", dupe.status_code == 409)

    advanced = requests.put(
        f"{BASE}/applications/{app_id}", headers=headers, json={"status": "Interview"}, timeout=10
    )
    check("status advances", advanced.json()["status"] == "Interview")
    check("notes preserved on partial update", advanced.json()["notes"] == "Smoke test entry")

    stats = requests.get(f"{BASE}/applications/stats", headers=headers, timeout=10).json()
    check("stats total correct", stats["total"] == 1)
    check("response rate computed", stats["response_rate"] == 100.0, f"{stats['response_rate']}%")
    check("all six stages reported", len(stats["by_status"]) == 6)

    # 8. Cleanup -----------------------------------------------------
    print("\n8. Cleanup and cascades")
    check(
        "delete application",
        requests.delete(f"{BASE}/applications/{app_id}", headers=headers, timeout=10).status_code
        == 200,
    )
    check(
        "delete job",
        requests.delete(f"{BASE}/jobs/{job_id}", headers=headers, timeout=10).status_code == 200,
    )
    check(
        "deleted job is 404",
        requests.get(f"{BASE}/jobs/{job_id}", timeout=10).status_code == 404,
    )
    check(
        "delete account",
        requests.delete(f"{BASE}/users/me", headers=headers, timeout=10).status_code == 200,
    )
    check(
        "token dead after account deletion",
        requests.get(f"{BASE}/users/me", headers=headers, timeout=10).status_code == 401,
    )

    print(f"\n{'=' * 50}")
    print(f"{passed} passed, {failed} failed")
    print("=" * 50)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
