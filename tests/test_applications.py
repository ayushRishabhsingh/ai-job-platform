"""Application tracker tests."""

from fastapi.testclient import TestClient


def _track(client: TestClient, headers: dict, job_id: int, status: str = "Saved", **kwargs):
    return client.post(
        "/applications", headers=headers, json={"job_id": job_id, "status": status, **kwargs}
    )


def test_create_requires_auth(client: TestClient, sample_job):
    assert client.post("/applications", json={"job_id": sample_job.id}).status_code == 401


def test_track_a_job(client: TestClient, auth_headers: dict, sample_job):
    response = _track(client, auth_headers, sample_job.id, notes="Referred by a friend")
    assert response.status_code == 201
    body = response.json()
    assert body["job_id"] == sample_job.id
    assert body["status"] == "Saved"
    assert body["notes"] == "Referred by a friend"
    # The nested job is returned, so the frontend needs one call, not two.
    assert body["job"]["company"] == "Acme Corp"


def test_match_score_is_snapshotted_at_creation(client: TestClient, auth_headers: dict, sample_job):
    client.patch(
        "/users/me",
        headers=auth_headers,
        json={"extra_skills": ["Python", "FastAPI", "Docker", "AWS"], "years_experience": 1},
    )
    body = _track(client, auth_headers, sample_job.id).json()
    assert body["match_score_at_apply"] == 80.0

    # Changing the resume later must not rewrite history.
    client.patch("/users/me", headers=auth_headers, json={"extra_skills": ["Excel"]})
    refetched = client.get(f"/applications/{body['id']}", headers=auth_headers).json()
    assert refetched["match_score_at_apply"] == 80.0


def test_score_is_null_when_user_has_no_skills(client: TestClient, auth_headers: dict, sample_job):
    assert _track(client, auth_headers, sample_job.id).json()["match_score_at_apply"] is None


def test_cannot_track_the_same_job_twice(client: TestClient, auth_headers: dict, sample_job):
    _track(client, auth_headers, sample_job.id)
    duplicate = _track(client, auth_headers, sample_job.id)
    assert duplicate.status_code == 409
    assert "already tracking" in duplicate.json()["detail"].lower()


def test_two_users_can_track_the_same_job(
    client: TestClient, auth_headers: dict, second_user_headers: dict, sample_job
):
    assert _track(client, auth_headers, sample_job.id).status_code == 201
    assert _track(client, second_user_headers, sample_job.id).status_code == 201


def test_tracking_a_missing_job_is_404(client: TestClient, auth_headers: dict):
    assert _track(client, auth_headers, 9999).status_code == 404


def test_invalid_status_is_rejected(client: TestClient, auth_headers: dict, sample_job):
    response = _track(client, auth_headers, sample_job.id, status="Ghosted")
    assert response.status_code == 422


def test_list_only_returns_own_applications(
    client: TestClient, auth_headers: dict, second_user_headers: dict, job_pool
):
    _track(client, auth_headers, job_pool[0].id)
    _track(client, second_user_headers, job_pool[1].id)

    mine = client.get("/applications", headers=auth_headers).json()
    assert mine["total"] == 1
    assert mine["items"][0]["job_id"] == job_pool[0].id


def test_filter_by_status(client: TestClient, auth_headers: dict, job_pool):
    _track(client, auth_headers, job_pool[0].id, status="Applied")
    _track(client, auth_headers, job_pool[1].id, status="Interview")

    body = client.get("/applications", headers=auth_headers, params={"status": "Interview"}).json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "Interview"


def test_list_is_paginated(client: TestClient, auth_headers: dict, job_pool):
    for job in job_pool:
        _track(client, auth_headers, job.id)
    body = client.get("/applications", headers=auth_headers, params={"limit": 2}).json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert len(body["items"]) == 2


def test_advance_the_status(client: TestClient, auth_headers: dict, sample_job):
    created = _track(client, auth_headers, sample_job.id).json()
    response = client.put(
        f"/applications/{created['id']}",
        headers=auth_headers,
        json={"status": "Interview", "notes": "Round 2 on Friday"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Interview"
    assert response.json()["notes"] == "Round 2 on Friday"


def test_partial_update_leaves_other_fields_alone(
    client: TestClient, auth_headers: dict, sample_job
):
    created = _track(client, auth_headers, sample_job.id, notes="Keep me").json()
    updated = client.put(
        f"/applications/{created['id']}", headers=auth_headers, json={"status": "OA"}
    ).json()
    assert updated["status"] == "OA"
    assert updated["notes"] == "Keep me"


def test_cannot_touch_another_users_application(
    client: TestClient, auth_headers: dict, second_user_headers: dict, sample_job
):
    created = _track(client, auth_headers, sample_job.id).json()
    assert (
        client.get(f"/applications/{created['id']}", headers=second_user_headers).status_code == 404
    )
    assert (
        client.put(
            f"/applications/{created['id']}", headers=second_user_headers, json={"status": "Offer"}
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/applications/{created['id']}", headers=second_user_headers).status_code
        == 404
    )


def test_delete_application(client: TestClient, auth_headers: dict, sample_job):
    created = _track(client, auth_headers, sample_job.id).json()
    assert client.delete(f"/applications/{created['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/applications/{created['id']}", headers=auth_headers).status_code == 404


def test_deleting_then_retracking_is_allowed(client: TestClient, auth_headers: dict, sample_job):
    created = _track(client, auth_headers, sample_job.id).json()
    client.delete(f"/applications/{created['id']}", headers=auth_headers)
    assert _track(client, auth_headers, sample_job.id).status_code == 201


def test_stats_on_an_empty_tracker(client: TestClient, auth_headers: dict):
    body = client.get("/applications/stats", headers=auth_headers).json()
    assert body["total"] == 0
    assert body["response_rate"] == 0.0
    # Every stage is still reported, so a chart has all its bars.
    assert len(body["by_status"]) == 6


def test_stats_counts_and_response_rate(client: TestClient, auth_headers: dict, job_pool):
    _track(client, auth_headers, job_pool[0].id, status="Applied")
    _track(client, auth_headers, job_pool[1].id, status="Interview")
    _track(client, auth_headers, job_pool[2].id, status="Saved")

    body = client.get("/applications/stats", headers=auth_headers).json()
    assert body["total"] == 3
    counts = {row["status"]: row["count"] for row in body["by_status"]}
    assert counts["Applied"] == 1
    assert counts["Interview"] == 1
    assert counts["Saved"] == 1
    # 1 response (Interview) out of 2 that actually went out -> 50%.
    # "Saved" is not an application, so it stays out of the denominator.
    assert body["response_rate"] == 50.0


def test_stats_ignores_other_users(
    client: TestClient, auth_headers: dict, second_user_headers: dict, job_pool
):
    _track(client, auth_headers, job_pool[0].id, status="Applied")
    _track(client, second_user_headers, job_pool[1].id, status="Offer")
    assert client.get("/applications/stats", headers=auth_headers).json()["total"] == 1


def test_deleting_a_job_cascades_to_applications(
    client: TestClient, auth_headers: dict, db_session, sample_job
):
    _track(client, auth_headers, sample_job.id)
    client.delete(f"/jobs/{sample_job.id}", headers=auth_headers)
    assert client.get("/applications", headers=auth_headers).json()["total"] == 0
