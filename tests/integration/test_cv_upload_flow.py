import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.config import settings
from app.deps import get_db
from app.main import app
from app.schemas.cv_schema import ExtractedCV
from app.schemas.improvement_schema import Improvement, ImprovementReport
from app.schemas.job_match_schema import JobMatch, JobMatchReport

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

FAKE_CV = ExtractedCV(
    full_name="Ama Owusu",
    email="ama@example.com",
    skills=["Python", "FastAPI"],
    years_of_experience=4,
    experience=[],
    education=[],
)
FAKE_IMPROVEMENTS = ImprovementReport(
    overall_score=80,
    strengths=["Clear structure"],
    improvements=[Improvement(section="Summary", issue="vague", suggestion="add metrics", priority="high")],
)
FAKE_JOBS = JobMatchReport(
    matches=[
        JobMatch(job_title="Backend Engineer", match_score=88, reasoning="strong fit", apply_links=["https://example.com/jobs"])
    ]
)


@pytest.fixture
def client():
    fake_db = AsyncMongoMockClient()["cv_recommender_test"]
    app.dependency_overrides[get_db] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    return {"x-api-key": "test-key"}


def _upload_sample_cv(client, headers):
    with open(FIXTURES_DIR / "sample_cv.pdf", "rb") as f:
        return client.post(
            "/cv/upload",
            headers=headers,
            files={"file": ("sample_cv.pdf", f, "application/pdf")},
        )


def _wait_for_status(client, headers, candidate_id, target_status, attempts=20, delay=0.05):
    for _ in range(attempts):
        response = client.get(f"/cv/{candidate_id}", headers=headers)
        if response.json()["status"] == target_status:
            return response
        time.sleep(delay)
    return response


@patch("app.services.s3_service.upload_file", return_value="cvs/fake-key-sample_cv.pdf")
@patch("app.services.llm_service.match_jobs", return_value=FAKE_JOBS)
@patch("app.services.llm_service.generate_improvements", return_value=FAKE_IMPROVEMENTS)
@patch("app.services.llm_service.extract_cv_from_file", return_value=FAKE_CV)
def test_full_upload_to_analysis_flow(mock_extract, mock_improve, mock_jobs, mock_upload, client, auth_headers):
    upload_response = _upload_sample_cv(client, auth_headers)
    assert upload_response.status_code == 200
    body = upload_response.json()
    assert body["status"] == "processing"
    candidate_id = body["candidate_id"]

    status_response = _wait_for_status(client, auth_headers, candidate_id, "analyzed")
    assert status_response.json()["status"] == "analyzed"
    assert status_response.json()["full_name"] == "Ama Owusu"

    analysis_response = client.get(f"/cv/{candidate_id}/analysis", headers=auth_headers)
    assert analysis_response.status_code == 200
    analysis_body = analysis_response.json()
    assert analysis_body["extracted_profile"]["full_name"] == "Ama Owusu"
    assert analysis_body["improvements"][0]["priority"] == "high"
    assert analysis_body["job_matches"][0]["job_title"] == "Backend Engineer"

    jobs_response = client.post(
        "/jobs/recommendations", headers=auth_headers, json={"candidate_id": candidate_id}
    )
    assert jobs_response.status_code == 200
    assert jobs_response.json()["matches"][0]["match_score"] == 88

    mock_extract.assert_called_once()
    mock_improve.assert_called_once()
    mock_jobs.assert_called_once()
    mock_upload.assert_called_once()


@patch("app.services.s3_service.upload_file", return_value="cvs/fake-key.pdf")
@patch("app.services.llm_service.match_jobs", side_effect=RuntimeError("LLM provider down"))
@patch("app.services.llm_service.generate_improvements", return_value=FAKE_IMPROVEMENTS)
@patch("app.services.llm_service.extract_cv_from_file", return_value=FAKE_CV)
def test_pipeline_failure_marks_candidate_failed(mock_extract, mock_improve, mock_jobs, mock_upload, client, auth_headers):
    upload_response = _upload_sample_cv(client, auth_headers)
    candidate_id = upload_response.json()["candidate_id"]

    status_response = _wait_for_status(client, auth_headers, candidate_id, "failed")

    assert status_response.json()["status"] == "failed"


def test_upload_without_api_key_returns_401(client):
    with open(FIXTURES_DIR / "sample_cv.pdf", "rb") as f:
        response = client.post("/cv/upload", files={"file": ("sample_cv.pdf", f, "application/pdf")})
    assert response.status_code == 401


def test_get_unknown_candidate_returns_404(client, auth_headers):
    response = client.get("/cv/000000000000000000000000", headers=auth_headers)
    assert response.status_code == 404


def test_get_analysis_before_ready_returns_404(client, auth_headers):
    with patch("app.services.s3_service.upload_file", return_value="cvs/fake-key.pdf"):
        upload_response = _upload_sample_cv(client, auth_headers)
    candidate_id = upload_response.json()["candidate_id"]

    # No LLM mocks patched in this test, so the background pipeline will
    # fail fast (no real API key) - either way, analysis isn't ready yet.
    response = client.get(f"/cv/{candidate_id}/analysis", headers=auth_headers)
    assert response.status_code == 404


def test_get_analysis_for_unknown_candidate_returns_404(client, auth_headers):
    response = client.get("/cv/000000000000000000000000/analysis", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found"


def test_job_recommendations_for_unknown_candidate_returns_404(client, auth_headers):
    response = client.post(
        "/jobs/recommendations", headers=auth_headers, json={"candidate_id": "000000000000000000000000"}
    )
    assert response.status_code == 404
