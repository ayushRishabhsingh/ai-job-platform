"""Recommendation engine and skill-gap tests."""

from fastapi.testclient import TestClient

from app.services.matcher import (
    MatchStrategy,
    TfidfMatcher,
    blend,
    confidence_label,
    gap_advice,
    skill_overlap,
    weighted_overlap,
)


# ----------------------------------------------------------------------
# Unit tests: the scoring maths
# ----------------------------------------------------------------------
def test_overlap_matches_the_worked_example():
    """The example from the project spec: 3 of 5 required skills -> 60%."""
    user = ["Python", "C++", "Machine Learning", "FastAPI", "Docker", "AWS"]
    job = ["Python", "PyTorch", "AWS", "Docker", "Kubernetes"]
    result = skill_overlap(user, job)
    assert result.score == 60.0
    assert result.matched_skills == ["Python", "AWS", "Docker"]
    assert result.missing_skills == ["PyTorch", "Kubernetes"]
    assert result.coverage == "3/5 skills"


def test_perfect_match_is_100():
    result = skill_overlap(["Python", "Docker"], ["Python", "Docker"])
    assert result.score == 100.0
    assert result.missing_skills == []


def test_no_match_is_zero():
    assert skill_overlap(["Excel"], ["Rust", "Go"]).score == 0.0


def test_extra_user_skills_do_not_inflate_score():
    """Only the job's requirements count towards the denominator."""
    a = skill_overlap(["Python"], ["Python", "Docker"])
    b = skill_overlap(["Python", "Excel", "Tableau", "Kafka"], ["Python", "Docker"])
    assert a.score == b.score == 50.0


def test_matching_is_case_and_alias_insensitive():
    result = skill_overlap(["python", "postgres"], ["Python", "PostgreSQL"])
    assert result.score == 100.0


def test_job_with_no_skills_scores_zero_not_crash():
    assert skill_overlap(["Python"], []).score == 0.0


def test_underqualified_is_penalised():
    user, job = ["Python", "Docker"], ["Python", "Docker"]
    assert weighted_overlap(user, job, user_experience=0, job_experience=3).score == 85.0


def test_overqualified_penalty_is_small():
    user, job = ["Python", "Docker"], ["Python", "Docker"]
    score = weighted_overlap(user, job, user_experience=8, job_experience=1).score
    assert 94.0 <= score <= 100.0


def test_penalty_never_goes_below_zero():
    score = weighted_overlap(["Excel"], ["Rust"], user_experience=0, job_experience=20).score
    assert score == 0.0


def test_tfidf_ranks_the_relevant_job_higher():
    matcher = TfidfMatcher(
        [
            "Python FastAPI Docker AWS backend API engineer",
            "React TypeScript CSS frontend designer",
        ]
    )
    scores = matcher.scores_for("Backend engineer building Python FastAPI services on AWS")
    assert scores[0] > scores[1]


def test_tfidf_handles_empty_corpus():
    assert TfidfMatcher([]).scores_for("anything") == []


def test_blend_keeps_the_explanation():
    overlap = skill_overlap(["Python"], ["Python", "Docker"])
    blended = blend(90.0, overlap, "tfidf")
    assert blended.matched_skills == ["Python"]
    assert blended.missing_skills == ["Docker"]
    assert overlap.score < blended.score < 90.0  # sits between the two inputs
    assert blended.strategy == "tfidf"


def test_confidence_labels():
    assert confidence_label(95) == "Strong match"
    assert confidence_label(65) == "Good match"
    assert confidence_label(45) == "Partial match"
    assert confidence_label(0) == "No match"


def test_gap_advice_is_specific():
    advice = gap_advice(["Kubernetes", "PyTorch"], 60.0)
    assert any("Kubernetes" in line for line in advice)


def test_gap_advice_for_perfect_match():
    assert "apply" in gap_advice([], 100.0)[0].lower()


# ----------------------------------------------------------------------
# HTTP tests
# ----------------------------------------------------------------------
def _set_skills(client: TestClient, headers: dict, skills: list[str], experience: int = 1):
    return client.patch(
        "/users/me",
        headers=headers,
        json={"extra_skills": skills, "years_experience": experience},
    )


def test_recommendations_require_auth(client: TestClient):
    assert client.get("/recommendations").status_code == 401


def test_recommendations_without_skills_is_400(client: TestClient, auth_headers: dict, job_pool):
    response = client.get("/recommendations", headers=auth_headers)
    assert response.status_code == 400
    assert "resume" in response.json()["detail"].lower()


def test_recommendations_are_ranked(client: TestClient, auth_headers: dict, job_pool):
    _set_skills(client, auth_headers, ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"])
    body = client.get("/recommendations", headers=auth_headers).json()

    assert body["strategy"] == "overlap"
    assert body["total_jobs_scored"] == 3
    recs = body["recommendations"]
    assert recs[0]["title"] == "Python Backend Engineer"
    assert recs[0]["match_score"] == 100.0
    scores = [r["match_score"] for r in recs]
    assert scores == sorted(scores, reverse=True)


def test_recommendations_include_gap_breakdown(client: TestClient, auth_headers: dict, job_pool):
    _set_skills(client, auth_headers, ["Python", "Docker", "AWS"], experience=3)
    recs = client.get("/recommendations", headers=auth_headers).json()["recommendations"]
    ml = next(r for r in recs if r["title"] == "ML Engineer")
    assert set(ml["matched_skills"]) == {"Python", "Docker", "AWS"}
    assert set(ml["missing_skills"]) == {"PyTorch", "Kubernetes"}


def test_min_score_filters_weak_matches(client: TestClient, auth_headers: dict, job_pool):
    _set_skills(client, auth_headers, ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"])
    body = client.get("/recommendations", headers=auth_headers, params={"min_score": 50}).json()
    assert all(r["match_score"] >= 50 for r in body["recommendations"])
    assert not any(r["title"] == "Frontend Developer" for r in body["recommendations"])


def test_limit_is_respected(client: TestClient, auth_headers: dict, job_pool):
    _set_skills(client, auth_headers, ["Python"])
    body = client.get("/recommendations", headers=auth_headers, params={"limit": 1}).json()
    assert len(body["recommendations"]) == 1


def test_location_filter_applies(client: TestClient, auth_headers: dict, job_pool):
    _set_skills(client, auth_headers, ["Python", "React"])
    body = client.get("/recommendations", headers=auth_headers, params={"location": "Pune"}).json()
    assert body["total_jobs_scored"] == 1
    assert body["recommendations"][0]["location"] == "Pune"


def test_tfidf_strategy_works_over_http(client: TestClient, auth_headers: dict, job_pool):
    _set_skills(client, auth_headers, ["Python", "FastAPI", "Docker", "AWS"])
    body = client.get("/recommendations", headers=auth_headers, params={"strategy": "tfidf"}).json()
    assert body["strategy"] == "tfidf"
    assert body["recommendations"][0]["title"] == "Python Backend Engineer"


def test_invalid_strategy_is_422(client: TestClient, auth_headers: dict, job_pool):
    _set_skills(client, auth_headers, ["Python"])
    response = client.get(
        "/recommendations", headers=auth_headers, params={"strategy": "telepathy"}
    )
    assert response.status_code == 422


def test_skill_gap_endpoint(client: TestClient, auth_headers: dict, sample_job):
    _set_skills(client, auth_headers, ["Python", "FastAPI", "Docker", "AWS"], experience=1)
    response = client.get(f"/jobs/{sample_job.id}/skill-gap", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["match_score"] == 80.0
    assert body["missing_skills"] == ["PostgreSQL"]
    assert body["coverage"] == "4/5 skills"
    assert body["advice"]
    assert body["job"]["id"] == sample_job.id


def test_skill_gap_for_missing_job_is_404(client: TestClient, auth_headers: dict):
    _set_skills(client, auth_headers, ["Python"])
    assert client.get("/jobs/9999/skill-gap", headers=auth_headers).status_code == 404


def test_all_declared_strategies_are_reported_by_health(client: TestClient):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert MatchStrategy.OVERLAP.value in body["match_strategies"]
    assert MatchStrategy.TFIDF.value in body["match_strategies"]
