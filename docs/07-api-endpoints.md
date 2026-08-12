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

## Sample route — `app/routers/cv.py`

```python
from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks
from app.deps import require_api_key, get_db
from app.services import s3_service, llm_service, mongo_service
from app.utils.file_parsing import to_image_bytes

router = APIRouter(prefix="/cv", tags=["cv"])

@router.post("/upload", dependencies=[Depends(require_api_key)])
async def upload_cv(background_tasks: BackgroundTasks, file: UploadFile = File(...), db=Depends(get_db)):
    raw = await file.read()
    s3_key = s3_service.upload_file(raw, file.filename)
    candidate = mongo_service.create_candidate(db, file.filename, s3_key)

    background_tasks.add_task(run_analysis_pipeline, candidate["_id"], raw, file.content_type, db)
    return {"candidate_id": str(candidate["_id"]), "status": "processing"}

def run_analysis_pipeline(candidate_id, raw_bytes, mime_type, db):
    image_bytes = to_image_bytes(raw_bytes, mime_type)   # normalize PDF/DOCX -> page images
    cv = llm_service.extract_cv_from_file(image_bytes, "image/png")
    improvements = llm_service.generate_improvements(cv)
    jobs = llm_service.match_jobs(cv)
    mongo_service.save_analysis(db, candidate_id, cv, improvements, jobs)
```

Two design points worth calling out:

- **`dependencies=[Depends(require_api_key)]` on the route decorator**, not
  inside the function body. FastAPI dependencies declared this way run *before*
  the handler and can short-circuit the request (raise `HTTPException`) without
  the route function needing to know auth exists at all. This is what keeps
  routers "thin" per [03-project-structure.md](03-project-structure.md) — the
  auth check is entirely decoupled from the upload logic.
- **`background_tasks.add_task(...)` is what makes `/cv/upload` return
  immediately.** FastAPI runs `run_analysis_pipeline` *after* the response has
  already been sent to the client. This is why the endpoint returns
  `status: "processing"` rather than the finished analysis — see
  [02-architecture.md](02-architecture.md) for the full polling flow this enables.
  Worth knowing as a scaling limitation: `BackgroundTasks` runs in-process, on
  the same EC2 instance that served the request. It's the right level of
  complexity for this project's scope, but if analysis volume grew large enough
  to need retry/backoff or cross-instance work distribution, the next step up
  would be a real task queue (Celery/SQS), not more `BackgroundTasks`.

See [16-concepts-glossary.md](16-concepts-glossary.md) for: dependency injection,
background task, multipart/form-data.
