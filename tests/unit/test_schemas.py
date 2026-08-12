import pytest
from pydantic import ValidationError

from app.schemas.cv_schema import ExtractedCV
from app.schemas.improvement_schema import Improvement, ImprovementReport
from app.schemas.job_match_schema import JobMatch, JobMatchReport


def test_extracted_cv_requires_full_name():
    data = {
        "full_name": "Ama Owusu",
        "skills": ["Python", "FastAPI"],
        "years_of_experience": 3.5,
        "experience": [],
        "education": [],
    }
    cv = ExtractedCV(**data)
    assert cv.full_name == "Ama Owusu"
    assert cv.years_of_experience == 3.5


def test_extracted_cv_missing_full_name_raises():
    with pytest.raises(ValidationError):
        ExtractedCV(skills=[], years_of_experience=0, experience=[], education=[])


def test_extracted_cv_nested_experience_validates():
    data = {
        "full_name": "Kwame Boateng",
        "skills": ["Go"],
        "years_of_experience": 2,
        "experience": [{"company": "Acme", "title": "Engineer", "summary": "Built things"}],
        "education": [],
    }
    cv = ExtractedCV(**data)
    assert cv.experience[0].company == "Acme"
    assert cv.experience[0].achievements == []


def test_extracted_cv_nested_experience_missing_field_raises():
    data = {
        "full_name": "Kwame Boateng",
        "skills": [],
        "years_of_experience": 2,
        "experience": [{"title": "Engineer", "summary": "Built things"}],  # missing company
        "education": [],
    }
    with pytest.raises(ValidationError):
        ExtractedCV(**data)


def test_improvement_rejects_invalid_priority():
    with pytest.raises(ValidationError):
        Improvement(section="Summary", issue="too vague", suggestion="add metrics", priority="urgent")


def test_improvement_report_rejects_out_of_range_score():
    with pytest.raises(ValidationError):
        ImprovementReport(overall_score=150, strengths=[], improvements=[])


def test_improvement_report_valid():
    report = ImprovementReport(
        overall_score=72,
        strengths=["Clear structure"],
        improvements=[
            Improvement(section="Summary", issue="too vague", suggestion="add metrics", priority="high")
        ],
    )
    assert report.overall_score == 72
    assert report.improvements[0].priority == "high"


def test_job_match_rejects_out_of_range_score():
    with pytest.raises(ValidationError):
        JobMatch(job_title="Backend Engineer", match_score=-1, reasoning="n/a", apply_links=[])


def test_job_match_report_valid():
    report = JobMatchReport(
        matches=[
            JobMatch(job_title="Backend Engineer", match_score=90, reasoning="strong fit", apply_links=["https://example.com"])
        ]
    )
    assert report.matches[0].skill_gaps == []
