"""Streamlit frontend.

This deliberately contains no business logic — it only talks HTTP to the
FastAPI backend, which is the whole point of building a REST API rather than
one monolithic Streamlit script.

Run the API first, then:
    streamlit run frontend/streamlit_app.py
"""

from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
TIMEOUT = 30

st.set_page_config(page_title="AI Job Matcher", page_icon="🎯", layout="wide")


# ----------------------------------------------------------------------
# API client
# ----------------------------------------------------------------------
def api(
    method: str,
    path: str,
    *,
    json: dict | None = None,
    params: dict | list | None = None,
    files: dict | None = None,
    data: dict | None = None,
    auth: bool = True,
) -> tuple[bool, dict | list | None, str]:
    """One call site for every request. Returns (ok, payload, error_message)."""
    headers: dict[str, str] = {}
    if auth and st.session_state.get("token"):
        headers["Authorization"] = f"Bearer {st.session_state['token']}"

    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            json=json,
            params=params,
            files=files,
            data=data,
            headers=headers,
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return False, None, f"Cannot reach the API at {API_BASE_URL} ({type(exc).__name__})"

    if response.status_code == 401 and auth:
        st.session_state.pop("token", None)
        return False, None, "Your session expired. Please log in again."

    if response.ok:
        payload = response.json() if response.content else None
        return True, payload, ""

    # Surface the API's own error message rather than a generic one.
    try:
        body = response.json()
        detail = body.get("detail", response.text)
        if isinstance(body.get("errors"), list):
            detail = "; ".join(f"{e['field']}: {e['message']}" for e in body["errors"])
    except ValueError:
        detail = response.text
    return False, None, f"{response.status_code}: {detail}"


def api_up() -> bool:
    ok, _, _ = api("GET", "/health", auth=False)
    return ok


# ----------------------------------------------------------------------
# Auth screens
# ----------------------------------------------------------------------
def render_auth() -> None:
    st.title("🎯 AI Job Matcher")
    st.caption("Upload your resume, get ranked job matches and see exactly which skills you lack.")

    if not api_up():
        st.error(
            f"The backend is not reachable at **{API_BASE_URL}**.\n\n"
            "Start it with `uvicorn app.main:app --reload`."
        )
        return

    login_tab, register_tab = st.tabs(["Log in", "Create account"])

    with login_tab:
        email = st.text_input("Email", key="login_email", placeholder="demo@example.com")
        password = st.text_input("Password", type="password", key="login_pw")
        if st.button("Log in", type="primary", use_container_width=True):
            ok, payload, error = api(
                "POST", "/auth/login", json={"email": email, "password": password}, auth=False
            )
            if ok:
                st.session_state["token"] = payload["access_token"]
                st.rerun()
            else:
                st.error(error)
        st.caption("Seeded demo account: `demo@example.com` / `demo12345`")

    with register_tab:
        new_email = st.text_input("Email", key="reg_email")
        new_name = st.text_input("Full name (optional)", key="reg_name")
        new_pw = st.text_input("Password (min 8 characters)", type="password", key="reg_pw")
        if st.button("Create account", use_container_width=True):
            ok, _, error = api(
                "POST",
                "/auth/register",
                json={"email": new_email, "password": new_pw, "full_name": new_name or None},
                auth=False,
            )
            if ok:
                st.success("Account created. Switch to the Log in tab.")
            else:
                st.error(error)


# ----------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------
def page_profile(profile: dict) -> None:
    st.header("Your profile")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Skills on file", len(profile["all_skills"]))
        st.metric("Years of experience", profile["years_experience"])
    with col2:
        st.metric("Active resume", "Yes" if profile["active_resume_id"] else "None")
        st.metric("Preferred location", profile["preferred_location"] or "Anywhere")

    if profile["all_skills"]:
        st.write("**Skills used for matching**")
        st.write(" · ".join(profile["all_skills"]))
    else:
        st.info("No skills yet. Upload a resume below, or add them manually.")

    st.divider()
    st.subheader("Upload a resume")
    uploaded = st.file_uploader("PDF, DOCX or TXT (max 5 MB)", type=["pdf", "docx", "txt"])
    if uploaded and st.button("Extract skills", type="primary"):
        with st.spinner("Parsing and extracting skills..."):
            ok, payload, error = api(
                "POST",
                "/resumes/upload",
                files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
            )
        if ok:
            st.success(payload["message"])
            st.write(" · ".join(payload["resume"]["skills"]) or "_none_")
            st.rerun()
        else:
            st.error(error)

    st.divider()
    st.subheader("Preferences")
    with st.form("prefs"):
        location = st.text_input("Preferred location", value=profile["preferred_location"] or "")
        experience = st.number_input(
            "Years of experience", min_value=0, max_value=60, value=profile["years_experience"]
        )
        extra = st.text_input(
            "Additional skills (comma separated)",
            value=", ".join(profile["extra_skills"]),
            help="Added on top of whatever the resume parser found.",
        )
        if st.form_submit_button("Save", type="primary"):
            ok, _, error = api(
                "PATCH",
                "/users/me",
                json={
                    "preferred_location": location or None,
                    "years_experience": int(experience),
                    "extra_skills": [s.strip() for s in extra.split(",") if s.strip()],
                },
            )
            st.success("Saved.") if ok else st.error(error)
            if ok:
                st.rerun()


def page_recommendations(profile: dict) -> None:
    st.header("Recommended jobs")

    if not profile["all_skills"]:
        st.warning("Add skills or upload a resume on the Profile page first.")
        return

    col1, col2, col3 = st.columns(3)
    strategy = col1.selectbox(
        "Strategy",
        ["overlap", "tfidf", "embedding"],
        help="overlap = skill match. tfidf/embedding = semantic similarity blended with overlap.",
    )
    min_score = col2.slider("Minimum match score", 0, 100, 0, step=5)
    limit = col3.number_input("How many", min_value=1, max_value=50, value=10)

    location = st.text_input(
        "Location filter (blank uses your saved preference)",
        placeholder=profile["preferred_location"] or "any",
    )

    with st.spinner("Scoring jobs..."):
        ok, payload, error = api(
            "GET",
            "/recommendations",
            params={
                "strategy": strategy,
                "min_score": min_score,
                "limit": int(limit),
                **({"location": location} if location else {}),
            },
        )

    if not ok:
        st.error(error)
        return

    recs = payload["recommendations"]
    st.caption(f"Scored {payload['total_jobs_scored']} jobs using `{payload['strategy']}`.")

    if not recs:
        st.info("Nothing cleared the score threshold. Try lowering it or widening the location.")
        return

    for rec in recs:
        score = rec["match_score"]
        with st.container(border=True):
            head, meter = st.columns([3, 1])
            head.markdown(f"### {rec['title']}")
            head.caption(
                f"{rec['company']} · {rec['location']} · {rec['experience_required']}+ years"
            )
            meter.metric("Match", f"{score:.0f}%")
            meter.progress(min(score / 100, 1.0))

            if rec["matched_skills"]:
                st.success("You have: " + ", ".join(rec["matched_skills"]))
            if rec["missing_skills"]:
                st.warning("Missing: " + ", ".join(rec["missing_skills"]))

            left, right = st.columns(2)
            if left.button("Skill-gap detail", key=f"gap_{rec['job_id']}"):
                ok_gap, gap, gap_error = api("GET", f"/jobs/{rec['job_id']}/skill-gap")
                if ok_gap:
                    st.info(f"**{gap['coverage']}** — {gap['match_score']:.0f}% match")
                    for line in gap["advice"]:
                        st.write(f"- {line}")
                else:
                    st.error(gap_error)
            if right.button("Save to tracker", key=f"save_{rec['job_id']}"):
                ok_save, _, save_error = api(
                    "POST", "/applications", json={"job_id": rec["job_id"], "status": "Saved"}
                )
                st.success("Saved.") if ok_save else st.error(save_error)


def page_browse() -> None:
    st.header("Browse all jobs")

    col1, col2, col3 = st.columns(3)
    query = col1.text_input("Search", placeholder="e.g. backend")
    location = col2.text_input("Location", placeholder="e.g. Bangalore")
    max_exp = col3.number_input("Max years required", min_value=0, max_value=40, value=40)

    col4, col5 = st.columns(2)
    sort_by = col4.selectbox("Sort by", ["created_at", "title", "company", "experience", "salary"])
    order = col5.selectbox("Order", ["desc", "asc"])

    params: dict = {"sort_by": sort_by, "order": order, "limit": 50, "max_experience": max_exp}
    if query:
        params["q"] = query
    if location:
        params["location"] = location

    ok, payload, error = api("GET", "/jobs", params=params, auth=False)
    if not ok:
        st.error(error)
        return

    st.caption(f"{payload['total']} matching jobs")
    if not payload["items"]:
        st.info("No jobs matched those filters.")
        return

    frame = pd.DataFrame(
        [
            {
                "Title": j["title"],
                "Company": j["company"],
                "Location": j["location"],
                "Exp": j["experience_required"],
                "Skills": ", ".join(j["skills"][:5]),
                "Salary (max)": j["salary_max"] or "—",
            }
            for j in payload["items"]
        ]
    )
    st.dataframe(frame, use_container_width=True, hide_index=True)


def page_tracker() -> None:
    st.header("Application tracker")

    ok_stats, stats, stats_error = api("GET", "/applications/stats")
    if ok_stats:
        cols = st.columns(len(stats["by_status"]) + 2)
        cols[0].metric("Total", stats["total"])
        cols[1].metric("Response rate", f"{stats['response_rate']:.0f}%")
        for i, row in enumerate(stats["by_status"], start=2):
            cols[i].metric(row["status"], row["count"])
    else:
        st.error(stats_error)

    st.divider()

    status_filter = st.selectbox(
        "Filter", ["All", "Saved", "Applied", "OA", "Interview", "Rejected", "Offer"]
    )
    params = {"limit": 50}
    if status_filter != "All":
        params["status"] = status_filter

    ok, payload, error = api("GET", "/applications", params=params)
    if not ok:
        st.error(error)
        return
    if not payload["items"]:
        st.info("Nothing tracked yet. Save a job from the Recommendations page.")
        return

    stages = ["Saved", "Applied", "OA", "Interview", "Rejected", "Offer"]
    for row in payload["items"]:
        job = row["job"]
        with st.container(border=True):
            left, mid, right = st.columns([3, 2, 1])
            left.markdown(f"**{job['title']}** — {job['company']}")
            left.caption(f"{job['location']} · tracked {row['created_at'][:10]}")
            if row["match_score_at_apply"] is not None:
                left.caption(f"Match when saved: {row['match_score_at_apply']:.0f}%")

            new_status = mid.selectbox(
                "Status",
                stages,
                index=stages.index(row["status"]),
                key=f"status_{row['id']}",
                label_visibility="collapsed",
            )
            if new_status != row["status"]:
                ok_up, _, up_error = api(
                    "PUT", f"/applications/{row['id']}", json={"status": new_status}
                )
                if ok_up:
                    st.rerun()
                else:
                    st.error(up_error)

            if right.button("Remove", key=f"del_{row['id']}"):
                ok_del, _, del_error = api("DELETE", f"/applications/{row['id']}")
                if ok_del:
                    st.rerun()
                else:
                    st.error(del_error)

            if row["notes"]:
                st.caption(f"📝 {row['notes']}")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main() -> None:
    if "token" not in st.session_state:
        render_auth()
        return

    ok, profile, error = api("GET", "/users/me")
    if not ok:
        st.error(error)
        if st.button("Back to login"):
            st.session_state.pop("token", None)
            st.rerun()
        return

    with st.sidebar:
        st.markdown(f"**{profile['full_name'] or profile['email']}**")
        st.caption(profile["email"])
        page = st.radio(
            "Go to",
            ["Recommendations", "Browse jobs", "Tracker", "Profile"],
            label_visibility="collapsed",
        )
        st.divider()
        if st.button("Log out", use_container_width=True):
            st.session_state.pop("token", None)
            st.rerun()
        st.caption(f"API: `{API_BASE_URL}`")

    if page == "Recommendations":
        page_recommendations(profile)
    elif page == "Browse jobs":
        page_browse()
    elif page == "Tracker":
        page_tracker()
    else:
        page_profile(profile)


if __name__ == "__main__":
    main()
