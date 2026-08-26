"""Auth and profile tests."""

from fastapi.testclient import TestClient

from app.core.security import hash_password, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("supersecret123")
    assert hashed != "supersecret123"
    assert verify_password("supersecret123", hashed)
    assert not verify_password("wrongpassword", hashed)


def test_register_returns_201_and_no_password(client: TestClient):
    response = client.post(
        "/auth/register", json={"email": "New@Example.com", "password": "password123"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"  # normalised to lower case
    assert "password" not in body and "hashed_password" not in body


def test_register_duplicate_email_conflicts(client: TestClient, registered_user: dict):
    response = client.post(
        "/auth/register", json={"email": "test@example.com", "password": "another123"}
    )
    assert response.status_code == 409


def test_register_rejects_short_password(client: TestClient):
    response = client.post("/auth/register", json={"email": "x@y.com", "password": "short"})
    assert response.status_code == 422


def test_register_rejects_invalid_email(client: TestClient):
    response = client.post(
        "/auth/register", json={"email": "not-an-email", "password": "password123"}
    )
    assert response.status_code == 422


def test_login_returns_bearer_token(client: TestClient, registered_user: dict):
    response = client.post(
        "/auth/login", json={"email": "test@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


def test_login_wrong_password_is_401(client: TestClient, registered_user: dict):
    response = client.post(
        "/auth/login", json={"email": "test@example.com", "password": "nope12345"}
    )
    assert response.status_code == 401


def test_login_unknown_email_gives_same_error(client: TestClient):
    """Must not leak whether an account exists."""
    response = client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": "whatever123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_oauth2_form_login_works(client: TestClient, registered_user: dict):
    """The flow the /docs Authorize button uses."""
    response = client.post(
        "/auth/token", data={"username": "test@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_me_requires_auth(client: TestClient):
    assert client.get("/users/me").status_code == 401


def test_me_rejects_garbage_token(client: TestClient):
    response = client.get("/users/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert response.status_code == 401


def test_me_returns_profile(client: TestClient, auth_headers: dict):
    response = client.get("/users/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "test@example.com"
    assert body["all_skills"] == []
    assert body["active_resume_id"] is None


def test_patch_me_updates_preferences(client: TestClient, auth_headers: dict):
    response = client.patch(
        "/users/me",
        headers=auth_headers,
        json={
            "preferred_location": "Chennai",
            "years_experience": 2,
            "extra_skills": ["Python", "python", " FastAPI "],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["preferred_location"] == "Chennai"
    assert body["years_experience"] == 2
    # De-duplicated and trimmed by the validator
    assert body["extra_skills"] == ["Python", "FastAPI"]
    assert body["all_skills"] == ["Python", "FastAPI"]


def test_patch_me_rejects_negative_experience(client: TestClient, auth_headers: dict):
    response = client.patch("/users/me", headers=auth_headers, json={"years_experience": -3})
    assert response.status_code == 422
