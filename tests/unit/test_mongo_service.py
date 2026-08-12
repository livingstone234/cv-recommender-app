import pytest
from mongomock_motor import AsyncMongoMockClient

from app.services import mongo_service


@pytest.fixture
def db():
    client = AsyncMongoMockClient()
    return client["cv_recommender_test"]


async def test_create_candidate_defaults_to_processing(db):
    candidate = await mongo_service.create_candidate(db, "resume.pdf", "cvs/abc-resume.pdf")

    assert candidate.id is not None
    assert candidate.status == "processing"
    assert candidate.full_name is None
    assert candidate.original_filename == "resume.pdf"
    assert candidate.cv_s3_key == "cvs/abc-resume.pdf"


async def test_get_candidate_round_trips(db):
    created = await mongo_service.create_candidate(db, "resume.pdf", "cvs/abc-resume.pdf")

    fetched = await mongo_service.get_candidate(db, created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.original_filename == "resume.pdf"


async def test_get_candidate_returns_none_when_missing(db):
    from bson import ObjectId

    fetched = await mongo_service.get_candidate(db, str(ObjectId()))

    assert fetched is None


async def test_save_analysis_marks_candidate_analyzed_and_fills_profile(db):
    candidate = await mongo_service.create_candidate(db, "resume.pdf", "cvs/abc-resume.pdf")

    extracted_profile = {"full_name": "Ama Owusu", "email": "ama@example.com", "skills": ["Python"]}
    analysis = await mongo_service.save_analysis(
        db,
        candidate.id,
        extracted_profile=extracted_profile,
        improvements=[{"section": "Summary", "issue": "too vague", "suggestion": "add metrics", "priority": "high"}],
        job_matches=[{"job_title": "Backend Engineer", "match_score": 90, "reasoning": "strong fit", "apply_links": []}],
    )

    assert analysis.candidate_id == candidate.id
    assert analysis.extracted_profile["full_name"] == "Ama Owusu"

    updated_candidate = await mongo_service.get_candidate(db, candidate.id)
    assert updated_candidate.status == "analyzed"
    assert updated_candidate.full_name == "Ama Owusu"
    assert updated_candidate.email == "ama@example.com"


async def test_get_analysis_round_trips(db):
    candidate = await mongo_service.create_candidate(db, "resume.pdf", "cvs/abc-resume.pdf")
    await mongo_service.save_analysis(
        db,
        candidate.id,
        extracted_profile={"full_name": "Ama Owusu"},
        improvements=[],
        job_matches=[],
    )

    fetched = await mongo_service.get_analysis(db, candidate.id)

    assert fetched is not None
    assert fetched.candidate_id == candidate.id


async def test_update_candidate_status(db):
    candidate = await mongo_service.create_candidate(db, "resume.pdf", "cvs/abc-resume.pdf")

    await mongo_service.update_candidate_status(db, candidate.id, "failed")

    updated = await mongo_service.get_candidate(db, candidate.id)
    assert updated.status == "failed"
