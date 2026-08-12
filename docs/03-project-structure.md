# 3. Folder Structure

```
cv-recommender-api/
├── app/
│   ├── main.py                    # FastAPI app entrypoint
│   ├── config.py                  # Settings (pydantic-settings), pulls from Secrets Manager
│   ├── deps.py                    # Dependency-injected DB client, API key auth
│   ├── auth/
│   │   └── api_key.py             # API key verification middleware
│   ├── models/
│   │   ├── candidate.py           # Mongo document models (Pydantic + Motor/PyMongo)
│   │   ├── analysis.py
│   │   └── job.py
│   ├── schemas/
│   │   ├── cv_schema.py           # Pydantic schema the LLM must return (structured CV)
│   │   ├── improvement_schema.py  # Pydantic schema for suggested edits
│   │   └── job_match_schema.py    # Pydantic schema for job recommendations
│   ├── routers/
│   │   ├── cv.py                  # /cv/upload, /cv/{id}
│   │   ├── analysis.py            # /cv/{id}/analysis
│   │   └── jobs.py                # /jobs/recommendations
│   ├── services/
│   │   ├── s3_service.py          # Upload/download to S3
│   │   ├── llm_service.py         # LangChain chains (extraction, improvement, matching)
│   │   ├── job_search_service.py  # Builds job-board search links (LinkedIn, Indeed, etc.)
│   │   └── mongo_service.py       # DB access layer
│   └── utils/
│       └── file_parsing.py        # PDF/DOCX -> text/image conversion helpers
├── tests/
│   ├── unit/
│   │   ├── test_llm_service.py
│   │   ├── test_s3_service.py
│   │   └── test_schemas.py
│   └── integration/
│       ├── test_cv_upload_flow.py
│       └── test_jobs_endpoint.py
├── .ebextensions/
│   └── 01_environment.config      # EB env config, pulls secrets at deploy
├── .github/
│   └── workflows/
│       ├── dev.yml
│       └── prod.yml
├── frontend/                      # Simple React UI (see 13-frontend.md)
├── Dockerfile
├── .dockerignore
├── requirements.txt                # runtime deps only - what ships in the image
├── requirements-dev.txt            # + pytest/moto/mongomock, for local dev & CI
├── pytest.ini
└── README.md
```

## Why it's organized this way (layered architecture)

This is a standard **routers → services → models/schemas** layering, which is
worth naming explicitly because it's the same shape you'll see in most non-trivial
FastAPI codebases:

- **`routers/`** — HTTP concerns only. Parses the request, calls a service function,
  shapes the response. No business logic, no direct DB/S3/LLM calls.
- **`services/`** — the actual business logic (talk to Mongo, talk to S3, talk to
  the LLM). Framework-agnostic — these functions don't know they're being called
  from a FastAPI route, which is exactly what makes them easy to unit test in
  isolation (see [10-testing-strategy.md](10-testing-strategy.md)).
- **`models/`** — what gets *persisted*. These describe MongoDB document shape.
- **`schemas/`** — what the *LLM* must return. These are a distinct concept from
  `models/` even though both are Pydantic classes — see
  [04-data-models.md](04-data-models.md) vs [05-llm-schemas.md](05-llm-schemas.md)
  for why they're kept separate rather than reusing one set of classes for both.
- **`deps.py`** — FastAPI's dependency injection lives here: things like "give me
  a DB connection" or "verify this request's API key" are declared once and
  attached to routes via `Depends(...)`, rather than re-instantiated per route.

## Naming rule of thumb while building

If you're about to write `boto3`, `pymongo`/`motor`, or an LLM provider SDK call
directly inside a file under `routers/`, stop — that logic belongs in `services/`.
Keeping routers thin is what makes the integration tests in
[10-testing-strategy.md](10-testing-strategy.md) able to mock at the service
boundary instead of mocking three different SDKs per test.
