# 10. Testing Strategy

## Unit vs integration, and why both

- **Unit tests** mock `boto3`, `langchain` LLM clients, and MongoDB to test
  business logic in isolation. These answer "does
  `job_search_service.build_search_links` produce the right URL for a title
  with special characters" without touching a network.
- **Integration tests** spin up a test MongoDB and use FastAPI's `TestClient`,
  hitting real routers end-to-end **with LLM calls mocked**. These answer
  "does `POST /cv/upload` actually create a candidate, return the right
  shape, and set status correctly" — the wiring between router → service →
  DB, which unit tests of individual services can't catch.

**A driver-specific correction:** plain `mongomock` only fakes the
*synchronous* PyMongo API. Since [04-data-models.md](04-data-models.md)
establishes that this project uses **Motor** (async) throughout, the actual
in-memory fake used is `mongomock-motor`'s `AsyncMongoMockClient` — a thin
async wrapper around `mongomock` that matches Motor's `await`-based API. Same
idea (no real MongoDB process needed), just the async-compatible variant.

The equivalent for `boto3`/S3 is **`moto`**'s `mock_aws()` context manager
(see [09-s3-storage.md](09-s3-storage.md)) — same "fake the whole service
in-memory" idea, and it comes with a real gotcha worth knowing before you hit
it: `boto3` clients cache credential resolution permanently on their *first*
real API call. A client built at import time, before test setup has run,
gets stuck failing forever even if the environment is fixed afterward —
which is why `app/services/s3_service.py` builds its client lazily on first
use rather than as a module-level singleton.

LLM calls are mocked in *both* tiers — never call a real OpenAI/Gemini API in
CI. That would make tests slow, flaky (network-dependent), non-deterministic
(LLMs aren't guaranteed to return identical output twice), and cost real money
on every CI run. What's being tested is *your code's* handling of the LLM
response — the request shape, the schema validation, the error handling — not
the LLM provider itself.

- **Coverage target: ≥ 80%**, enforced in CI (`pytest --cov=app --cov-fail-under=80`).

## Example unit test — `tests/unit/test_schemas.py`

```python
from app.schemas.cv_schema import ExtractedCV

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
```

This is testing the *schema itself* — that valid data constructs correctly, and
(worth adding alongside this) that invalid data (missing `full_name`, a string
where `years_of_experience` expects a float) raises `pydantic.ValidationError`.
Schema tests like this are cheap to write and catch schema regressions before
they ever reach an LLM call.

## Example integration test — `tests/integration/test_cv_upload_flow.py`

```python
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

@patch("app.services.s3_service.upload_file", return_value="cvs/fake-key.pdf")
def test_upload_cv_returns_processing_status(mock_upload):
    with open("tests/fixtures/sample_cv.pdf", "rb") as f:
        response = client.post(
            "/cv/upload",
            headers={"x-api-key": "test-key"},
            files={"file": ("sample_cv.pdf", f, "application/pdf")},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
```

`@patch("app.services.s3_service.upload_file", ...)` patches at the **service**
boundary, not deep inside `boto3` — this is only possible because routers call
services and services call SDKs, per the layering in
[03-project-structure.md](03-project-structure.md). If the router called
`boto3` directly, this test would need to mock the AWS SDK client instead,
which is far more brittle (tied to `boto3`'s API shape, not your own).

## `pytest.ini`

```ini
[pytest]
testpaths = tests
addopts = --cov=app --cov-report=term-missing --cov-fail-under=80
```

This makes `pytest` (no flags) behave the same locally as it does in CI — the
coverage gate isn't something you only discover when a PR fails; you see it on
every local run too.

See [16-concepts-glossary.md](16-concepts-glossary.md) for: mocking/patching,
test fixtures, coverage.
