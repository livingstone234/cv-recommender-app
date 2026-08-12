# 15. Build Roadmap

The PDF (and docs 01-14) describe the *finished* system. This is the order
we'll actually build it in — inside-out: core logic first, with everything
mockable/local, AWS last. Each milestone should end in a working, tested state
before moving to the next; don't start AWS until the app runs correctly on
your machine end-to-end.

## Milestone 1 — Scaffold
- Repo structure per [03-project-structure.md](03-project-structure.md).
- `requirements.txt`, `pytest.ini`, `.gitignore` (`.env`, `__pycache__`, etc.).
- `app/config.py` with `pydantic-settings`, loading from `.env` locally.
- A local MongoDB via `docker-compose` (no Atlas/AWS needed yet).
- **Done when:** `uvicorn app.main:app --reload` boots and `GET /health` returns 200.

## Milestone 2 — Data layer
- `app/models/candidate.py`, `analysis.py` ([04-data-models.md](04-data-models.md)).
- `app/services/mongo_service.py` — create/read candidate, save analysis.
- **Done when:** you can create and fetch a `Candidate` document against the
  local Mongo, with a unit test using `mongomock`.

## Milestone 3 — LLM output schemas (no LLM calls yet)
- `app/schemas/cv_schema.py`, `improvement_schema.py`, `job_match_schema.py`
  ([05-llm-schemas.md](05-llm-schemas.md)).
- Unit tests for valid/invalid construction of each schema — this is pure
  Pydantic, no network calls, fast to get right.

## Milestone 4 — Auth
- `app/auth/api_key.py`, `app/deps.py` ([08-authentication.md](08-authentication.md)).
- Wire a placeholder protected route and confirm a bad/missing key 401s.

## Milestone 5 — File handling + S3
- `app/services/s3_service.py` ([09-s3-storage.md](09-s3-storage.md)) — test
  against a mocked S3 (`moto` library) rather than a real bucket.
- `app/utils/file_parsing.py` — `to_image_bytes` for PDF/DOCX → page images.
  This is a good milestone to sanity-check manually: feed it a real sample CV
  PDF and confirm you get back valid PNG bytes per page.

## Milestone 6 — LangChain pipeline (first real LLM calls)
- `app/services/llm_service.py` ([06-langchain-pipeline.md](06-langchain-pipeline.md)).
- Get `extract_cv_from_file` working against **one real API key** (OpenAI is
  fine to start; add Gemini once the pattern works) on a real sample CV before
  building the other two chains — validate the multimodal call actually works
  before layering more on top.
- Then `generate_improvements` and `match_jobs`.
- `app/services/job_search_service.py` — deterministic link builder, unit-testable
  with no LLM involved.

## Milestone 7 — Wire the routers
- `app/routers/cv.py`, `analysis.py`, `jobs.py` ([07-api-endpoints.md](07-api-endpoints.md)).
- The `BackgroundTasks` pipeline end-to-end: upload → S3 → background analysis
  → Mongo → status flips to `"analyzed"`.
- **Done when:** you can `curl -F file=@sample_cv.pdf` against `/cv/upload`,
  poll `/cv/{id}`, and eventually see a real `ImprovementReport` and
  `JobMatchReport` come back from `/cv/{id}/analysis` and
  `/jobs/recommendations`.

## Milestone 8 — Test coverage to the gate
- Fill out `tests/unit/` and `tests/integration/` per
  [10-testing-strategy.md](10-testing-strategy.md) until
  `pytest --cov=app --cov-fail-under=80` passes locally.

## Milestone 9 — Dockerize
- `Dockerfile` for the backend (remember `poppler-utils` as a system
  dependency for `pdf2image` — see
  [14-environment-and-requirements.md](14-environment-and-requirements.md)).
- Confirm `docker build` + `docker run` works locally before touching AWS.

## Milestone 10 — Frontend
- React upload/results screens ([13-frontend.md](13-frontend.md)) against the
  local backend.
- **Done when:** you can drag-drop a CV in the browser and see real results
  render.

## Milestone 11 — AWS infrastructure
- S3 buckets (uploads + frontend), Secrets Manager secret, IAM roles/policies,
  VPC/subnets/NAT, Elastic Beanstalk application + environment, ALB, CloudFront
  ([11-aws-infrastructure.md](11-aws-infrastructure.md)).
- Stand up **dev only** first. Get one successful manual deploy working before
  automating it.

## Milestone 12 — CI/CD
- `.github/workflows/dev.yml` ([12-cicd.md](12-cicd.md)) — push to `develop`
  deploys automatically to the dev environment.
- Once dev is solid, stand up the prod AWS environment and `prod.yml`.
- Frontend deploy pipeline (S3 sync + CloudFront invalidation).

## Milestone 13 — Polish for your CV/portfolio
- README with architecture diagram, a short demo GIF/video, and an explicit
  "what I'd do differently at scale" section (task queue instead of
  `BackgroundTasks`, multi-tenant API keys, etc. — see the scope notes
  scattered through docs 01-13). Being able to name the deliberate scope
  boundaries, not just the features, is what separates "I followed a tutorial"
  from "I made engineering tradeoffs" in how this reads to someone reviewing
  your GitHub.

## A note on pacing

Don't skip ahead to AWS because it feels like "the impressive part." The
LangChain/Pydantic structured-output pipeline (Milestones 3, 6) is the part
most worth understanding deeply — it's what you'll be asked to explain in
detail if this comes up in an interview, far more than "I clicked through the
Elastic Beanstalk console."
