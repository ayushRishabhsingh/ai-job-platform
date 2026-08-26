"""Job CRUD, filtering, sorting and pagination tests."""

from fastapi.testclient import TestClient

from tests.conftest import SAMPLE_JOB


def test_create_job_requires_auth(client: TestClient):
    assert client.post("/jobs", json=SAMPLE_JOB).status_code == 401


def test_create_job(client: TestClient, auth_headers: dict):
    response = client.post("/jobs", json=SAMPLE_JOB, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Backend Engineer"
    assert body["skills"] == SAMPLE_JOB["skills"]
    assert body["is_active"] is True
    assert body["id"] > 0


def test_create_job_deduplicates_skills(client: TestClient, auth_headers: dict):
    payload = {**SAMPLE_JOB, "skills": ["Python", "python", " PYTHON ", "Docker"]}
    response = client.post("/jobs", json=payload, headers=auth_headers)
    assert response.json()["skills"] == ["Python", "Docker"]


def test_create_job_rejects_inverted_salary(client: TestClient, auth_headers: dict):
    payload = {**SAMPLE_JOB, "salary_min": 2000000, "salary_max": 1000000}
    response = client.post("/jobs", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_get_job(client: TestClient, sample_job):
    response = client.get(f"/jobs/{sample_job.id}")
    assert response.status_code == 200
    assert response.json()["company"] == "Acme Corp"


def test_get_missing_job_is_404(client: TestClient):
    response = client.get("/jobs/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_jobs_is_public_and_paginated(client: TestClient, job_pool):
    response = client.get("/jobs")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["pages"] == 1
    assert len(body["items"]) == 3


def test_pagination_splits_pages(client: TestClient, job_pool):
    page1 = client.get("/jobs", params={"limit": 2, "page": 1}).json()
    page2 = client.get("/jobs", params={"limit": 2, "page": 2}).json()
    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 1
    assert page1["total"] == page2["total"] == 3
    assert page1["pages"] == 2
    ids = {j["id"] for j in page1["items"]} | {j["id"] for j in page2["items"]}
    assert len(ids) == 3  # no overlap between pages


def test_filter_by_location(client: TestClient, job_pool):
    body = client.get("/jobs", params={"location": "bangalore"}).json()
    assert body["total"] == 2
    assert all("Bangalore" in j["location"] for j in body["items"])


def test_filter_by_single_skill(client: TestClient, job_pool):
    body = client.get("/jobs", params={"skill": "PyTorch"}).json()
    assert body["total"] == 1
    assert body["items"][0]["company"] == "Gamma"


def test_filter_by_multiple_skills_is_and(client: TestClient, job_pool):
    body = client.get("/jobs", params=[("skill", "Python"), ("skill", "Kubernetes")]).json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "ML Engineer"


def test_skill_filter_is_case_insensitive(client: TestClient, job_pool):
    body = client.get("/jobs", params={"skill": "python"}).json()
    assert body["total"] == 2


def test_free_text_search(client: TestClient, job_pool):
    body = client.get("/jobs", params={"q": "react"}).json()
    assert body["total"] == 1
    assert body["items"][0]["company"] == "Beta"


def test_experience_range_filter(client: TestClient, job_pool):
    body = client.get("/jobs", params={"max_experience": 1}).json()
    assert body["total"] == 1
    assert body["items"][0]["experience_required"] == 1


def test_sorting_by_title_ascending(client: TestClient, job_pool):
    body = client.get("/jobs", params={"sort_by": "title", "order": "asc"}).json()
    titles = [j["title"] for j in body["items"]]
    assert titles == sorted(titles)


def test_invalid_sort_field_is_422(client: TestClient, job_pool):
    assert client.get("/jobs", params={"sort_by": "salary_lol"}).status_code == 422


def test_update_job(client: TestClient, auth_headers: dict):
    created = client.post("/jobs", json=SAMPLE_JOB, headers=auth_headers).json()
    response = client.put(
        f"/jobs/{created['id']}",
        json={"title": "Senior Backend Engineer", "experience_required": 4},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Senior Backend Engineer"
    assert body["experience_required"] == 4
    assert body["company"] == "Acme Corp"  # untouched fields survive


def test_cannot_update_someone_elses_job(
    client: TestClient, auth_headers: dict, second_user_headers: dict
):
    created = client.post("/jobs", json=SAMPLE_JOB, headers=auth_headers).json()
    response = client.put(
        f"/jobs/{created['id']}", json={"title": "Hijacked"}, headers=second_user_headers
    )
    assert response.status_code == 403


def test_delete_job(client: TestClient, auth_headers: dict):
    created = client.post("/jobs", json=SAMPLE_JOB, headers=auth_headers).json()
    assert client.delete(f"/jobs/{created['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/jobs/{created['id']}").status_code == 404


def test_soft_deactivated_jobs_are_hidden_by_default(client: TestClient, auth_headers: dict):
    created = client.post("/jobs", json=SAMPLE_JOB, headers=auth_headers).json()
    client.put(f"/jobs/{created['id']}", json={"is_active": False}, headers=auth_headers)
    assert client.get("/jobs").json()["total"] == 0
    assert client.get("/jobs", params={"is_active": False}).json()["total"] == 1
