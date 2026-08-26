"""Resume upload, parsing and skill-extraction tests."""

from fastapi.testclient import TestClient

from app.services.resume_parser import clean_text, split_sections
from app.services.skill_extractor import extract_skills


# ----------------------------------------------------------------------
# Unit tests: extraction logic, no HTTP
# ----------------------------------------------------------------------
def test_extract_basic_skills():
    skills = extract_skills("I write Python and use FastAPI with PostgreSQL.")
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "PostgreSQL" in skills


def test_extract_handles_aliases():
    skills = extract_skills("Experienced with sklearn, k8s, postgres and nodejs.")
    assert "Scikit-learn" in skills
    assert "Kubernetes" in skills
    assert "PostgreSQL" in skills
    assert "Node.js" in skills


def test_cpp_does_not_leak_into_c():
    """'C' must not be matched from inside 'C++'."""
    assert extract_skills("Proficient in C++ and Python") == ["C++", "Python"]


def test_c_is_detected_when_standalone():
    skills = extract_skills("Languages: C, C++, Python")
    assert "C" in skills and "C++" in skills


def test_short_aliases_require_upper_case():
    """'ml' inside 'html' must not become Machine Learning."""
    skills = extract_skills("I write html and css templates")
    assert "Machine Learning" not in skills
    assert "HTML" in skills


def test_ambiguous_bare_words_are_ignored():
    skills = extract_skills("I go to the office and the R&D team is great")
    assert "Go" not in skills
    assert "R" not in skills


def test_empty_text_returns_empty_list():
    assert extract_skills("") == []


def test_skills_section_is_ranked_first():
    text = clean_text(
        "SKILLS\nKubernetes\n\nEXPERIENCE\nUsed Python extensively, Python everywhere, Python."
    )
    sections = split_sections(text)
    skills = extract_skills(text, sections)
    # Kubernetes is declared in SKILLS, so it outranks the more frequent Python.
    assert skills.index("Kubernetes") < skills.index("Python")


def test_section_splitting():
    text = clean_text("TECHNICAL SKILLS\nPython\n\nEDUCATION\nB.Tech EEE\n\nPROJECTS\nRAG bot")
    sections = split_sections(text)
    assert set(sections) >= {"skills", "education", "projects"}
    assert "Python" in sections["skills"]


# ----------------------------------------------------------------------
# HTTP tests: the upload pipeline
# ----------------------------------------------------------------------
def test_upload_requires_auth(client: TestClient, resume_pdf_bytes: bytes):
    response = client.post(
        "/resumes/upload", files={"file": ("cv.pdf", resume_pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 401


def test_upload_pdf_extracts_skills(
    client: TestClient, auth_headers: dict, resume_pdf_bytes: bytes
):
    response = client.post(
        "/resumes/upload",
        headers=auth_headers,
        files={"file": ("cv.pdf", resume_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["skills_found"] > 0
    skills = body["resume"]["skills"]
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "Docker" in skills
    assert body["resume"]["page_count"] == 1
    assert body["resume"]["word_count"] > 0
    assert body["resume"]["is_active"] is True


def test_upload_txt_works(client: TestClient, auth_headers: dict):
    content = b"SKILLS\nPython, SQL, Power BI, Excel"
    response = client.post(
        "/resumes/upload",
        headers=auth_headers,
        files={"file": ("cv.txt", content, "text/plain")},
    )
    assert response.status_code == 201
    assert "Power BI" in response.json()["resume"]["skills"]


def test_upload_rejects_unsupported_format(client: TestClient, auth_headers: dict):
    response = client.post(
        "/resumes/upload",
        headers=auth_headers,
        files={"file": ("photo.png", b"\x89PNG\r\n", "image/png")},
    )
    assert response.status_code == 415


def test_uploaded_skills_appear_on_profile(
    client: TestClient, auth_headers: dict, resume_pdf_bytes: bytes
):
    client.post(
        "/resumes/upload",
        headers=auth_headers,
        files={"file": ("cv.pdf", resume_pdf_bytes, "application/pdf")},
    )
    profile = client.get("/users/me", headers=auth_headers).json()
    assert "Python" in profile["all_skills"]
    assert profile["active_resume_id"] is not None


def test_only_one_resume_stays_active(
    client: TestClient, auth_headers: dict, resume_pdf_bytes: bytes
):
    files = {"file": ("cv.pdf", resume_pdf_bytes, "application/pdf")}
    first = client.post("/resumes/upload", headers=auth_headers, files=files).json()["resume"]
    client.post(
        "/resumes/upload",
        headers=auth_headers,
        files={"file": ("cv2.pdf", resume_pdf_bytes, "application/pdf")},
    )
    listing = client.get("/resumes", headers=auth_headers).json()
    assert listing["total"] == 2
    active = [r for r in listing["items"] if r["is_active"]]
    assert len(active) == 1
    assert active[0]["id"] != first["id"]


def test_reactivate_older_resume(client: TestClient, auth_headers: dict, resume_pdf_bytes: bytes):
    files = {"file": ("cv.pdf", resume_pdf_bytes, "application/pdf")}
    first = client.post("/resumes/upload", headers=auth_headers, files=files).json()["resume"]
    client.post("/resumes/upload", headers=auth_headers, files=files)
    response = client.post(f"/resumes/{first['id']}/activate", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_patch_skills_add_and_remove(
    client: TestClient, auth_headers: dict, resume_pdf_bytes: bytes
):
    resume = client.post(
        "/resumes/upload",
        headers=auth_headers,
        files={"file": ("cv.pdf", resume_pdf_bytes, "application/pdf")},
    ).json()["resume"]

    response = client.patch(
        f"/resumes/{resume['id']}/skills",
        headers=auth_headers,
        json={"add": ["Kubernetes", "k8s"], "remove": ["Docker"]},
    )
    assert response.status_code == 200
    skills = response.json()["skills"]
    assert "Kubernetes" in skills
    assert skills.count("Kubernetes") == 1  # alias collapsed, not duplicated
    assert "Docker" not in skills


def test_cannot_read_another_users_resume(
    client: TestClient, auth_headers: dict, second_user_headers: dict, resume_pdf_bytes: bytes
):
    resume = client.post(
        "/resumes/upload",
        headers=auth_headers,
        files={"file": ("cv.pdf", resume_pdf_bytes, "application/pdf")},
    ).json()["resume"]
    response = client.get(f"/resumes/{resume['id']}", headers=second_user_headers)
    assert response.status_code == 404  # 404 not 403, so ids are not enumerable


def test_raw_text_is_opt_in(client: TestClient, auth_headers: dict, resume_pdf_bytes: bytes):
    resume = client.post(
        "/resumes/upload",
        headers=auth_headers,
        files={"file": ("cv.pdf", resume_pdf_bytes, "application/pdf")},
    ).json()["resume"]

    without = client.get(f"/resumes/{resume['id']}", headers=auth_headers).json()
    assert without["raw_text"] is None

    with_text = client.get(
        f"/resumes/{resume['id']}", headers=auth_headers, params={"include_text": True}
    ).json()
    assert "Python" in with_text["raw_text"]


def test_delete_resume(client: TestClient, auth_headers: dict, resume_pdf_bytes: bytes):
    resume = client.post(
        "/resumes/upload",
        headers=auth_headers,
        files={"file": ("cv.pdf", resume_pdf_bytes, "application/pdf")},
    ).json()["resume"]
    assert client.delete(f"/resumes/{resume['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/resumes/{resume['id']}", headers=auth_headers).status_code == 404
