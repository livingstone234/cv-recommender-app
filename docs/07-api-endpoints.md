# 7. API Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/cv/upload` | Multipart upload of CV file → stores raw file in S3, creates `Candidate` doc, kicks off async analysis | API Key |
| GET | `/cv/{candidate_id}` | Get candidate metadata + status | API Key |
| GET | `/cv/{candidate_id}/analysis` | Get extracted profile + improvement report | API Key |
| POST | `/jobs/recommendations` | Body: `{candidate_id}` → returns `JobMatchReport` with real search links | API Key |
| GET | `/health` | Liveness/readiness probe for ALB | none |

`/health` is deliberately unauthenticated — the Application Load Balancer's
health check (see [11-aws-infrastructure.md](11-aws-infrastructure.md#114-application-load-balancer))
hits this route constantly to decide whether an EC2 instance is serving traffic,
and it has no business needing an API key to answer "is this process alive".

## Router layout — one file per concern, sharing the `/cv` prefix

Per [03-project-structure.md](03-project-structure.md), `/cv/upload` and
`GET /cv/{id}` live in `app/routers/cv.py`; `GET /cv/{id}/analysis` gets its
own `app/routers/analysis.py`, even though it shares the same URL prefix —
kept separate because it's a distinct concern (reading a *result*, not
managing the candidate record), each with its own `APIRouter(prefix="/cv",
...)` mounted onto the app in `main.py`. `/jobs/recommendations` is
`app/routers/jobs.py`. All three declare `dependencies=[Depends(require_api_key)]`
at the **router** level (not per-route) — every path under each of these
requires the API key, which matches the endpoints table above without
repeating the dependency on every single route function.

## `app/routers/cv.py`

```python
import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from app.deps import get_db, require_api_key
from app.services import llm_service, mongo_service, s3_service
from app.utils.file_parsing import to_image_bytes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cv", tags=["cv"], dependencies=[Depends(require_api_key)])

@router.post("/upload")
async def upload_cv(background_tasks: BackgroundTasks, file: UploadFile = File(...), db=Depends(get_db)):
    raw = await file.read()
    s3_key = await asyncio.to_thread(s3_service.upload_file, raw, file.filename)
    candidate = await mongo_service.create_candidate(db, file.filename, s3_key)

    background_tasks.add_task(run_analysis_pipeline, candidate.id, raw, file.content_type, db)
    return {"candidate_id": candidate.id, "status": candidate.status}

@router.get("/{candidate_id}")
async def get_candidate(candidate_id: str, db=Depends(get_db)):
    candidate = await mongo_service.get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate

async def run_analysis_pipeline(candidate_id, raw_bytes, mime_type, db):
    try:
        page_images = await asyncio.to_thread(to_image_bytes, raw_bytes, mime_type)
        cv = await asyncio.to_thread(llm_service.extract_cv_from_file, page_images)
        improvements, jobs = await asyncio.gather(
            asyncio.to_thread(llm_service.generate_improvements, cv),
            asyncio.to_thread(llm_service.match_jobs, cv),
        )
        await mongo_service.save_analysis(
            db, candidate_id,
            extracted_profile=cv.model_dump(),
            improvements=[i.model_dump() for i in improvements.improvements],
            job_matches=[m.model_dump() for m in jobs.matches],
        )
    except Exception:
        logger.exception("Analysis pipeline failed for candidate %s", candidate_id)
        await mongo_service.update_candidate_status(db, candidate_id, "failed")
```

Three real gaps came up while wiring this together, all caught by actually
running the code (not just reading it) and fixed here:

1. **Every service call in the original sketch is a *blocking* call
   (`boto3`, LangChain's `.invoke()`, `pdf2image`), but they're invoked from
   `async def` routes and an `async def` background task.** Calling a
   blocking function directly inside an async function stalls the *entire*
   event loop — every other in-flight request on the server — for however
   long that call takes, which for a 3-call LLM pipeline is easily
   10-30+ seconds. This is the exact failure mode
   [04-data-models.md](04-data-models.md) already explains for why Motor
   (async) is used over PyMongo — the same problem, just showing up in the S3
   and LLM calls instead of the DB call. Every blocking call is now wrapped
   in `await asyncio.to_thread(fn, ...)`, which runs it in a worker thread
   without blocking the loop, while `run_analysis_pipeline` itself stays
   `async def` so it can still `await` Motor calls directly.
2. **`generate_improvements` and `match_jobs` now run concurrently**
   (`asyncio.gather`) instead of sequentially — [06-langchain-pipeline.md](06-langchain-pipeline.md)
   had already flagged this as "worth doing once the sync version works."
   Since fixing the blocking-call issue meant touching this exact code path
   anyway, doing both calls at once (independent of each other) was a small
   addition that cuts the pipeline's slowest stretch roughly in half.
3. **The background task's `except` block used to re-raise after marking the
   candidate `"failed"`, to "preserve visibility in server logs."** That
   assumption turned out to be wrong in a way that only showed up by writing
   and running an integration test: `TestClient` executes background tasks
   as part of the same call stack as the request, and an unhandled exception
   there **propagates back through the test client's own `.post()` call**,
   crashing the test rather than returning a clean response. Since a real
   ASGI server's handling of an exception raised from inside a
   `BackgroundTask` is similarly not something to rely on, the fix is
   `logger.exception(...)` instead of `raise` — visibility without depending
   on ambient propagation behavior nobody actually guarantees.

Two design points from the original sketch still hold:

- **`dependencies=[Depends(require_api_key)]`**, now on the router rather
  than the individual route, runs *before* the handler and can short-circuit
  the request without the route function needing to know auth exists at all
  — keeps routers "thin" per [03-project-structure.md](03-project-structure.md).
- **`background_tasks.add_task(...)` is what makes `/cv/upload` return
  immediately**, before analysis is done — see
  [02-architecture.md](02-architecture.md) for the polling flow this enables.
  `BackgroundTasks` runs in-process, on the same EC2 instance that served the
  request; right for this project's scope, but if volume grew enough to need
  retry/backoff or cross-instance work distribution, the next step up is a
  real task queue (Celery/SQS), not more `BackgroundTasks`.

See [16-concepts-glossary.md](16-concepts-glossary.md) for: dependency injection,
background task, multipart/form-data.
