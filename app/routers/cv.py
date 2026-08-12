import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.deps import get_db, require_api_key
from app.models.candidate import Candidate
from app.services import llm_service, mongo_service, s3_service
from app.utils.file_parsing import to_image_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["cv"], dependencies=[Depends(require_api_key)])


@router.post("/upload")
async def upload_cv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    raw = await file.read()
    # s3_service.upload_file is a blocking boto3 call - offload it so it
    # doesn't stall the event loop (and every other in-flight request) for
    # the duration of the upload.
    s3_key = await asyncio.to_thread(s3_service.upload_file, raw, file.filename)
    candidate = await mongo_service.create_candidate(db, file.filename, s3_key)

    background_tasks.add_task(run_analysis_pipeline, candidate.id, raw, file.content_type, db)
    return {"candidate_id": candidate.id, "status": candidate.status}


@router.get("/{candidate_id}")
async def get_candidate(candidate_id: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> Candidate:
    candidate = await mongo_service.get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


async def run_analysis_pipeline(candidate_id: str, raw_bytes: bytes, mime_type: str, db: AsyncIOMotorDatabase) -> None:
    """Runs in the background after /cv/upload has already responded. Every
    step here is a blocking call (file conversion, LLM requests) run via
    asyncio.to_thread so it doesn't block the event loop for other requests
    while it works - a 3-call LLM pipeline can easily take 10-30+ seconds."""
    try:
        page_images = await asyncio.to_thread(to_image_bytes, raw_bytes, mime_type)
        cv = await asyncio.to_thread(llm_service.extract_cv_from_file, page_images)

        improvements, jobs = await asyncio.gather(
            asyncio.to_thread(llm_service.generate_improvements, cv),
            asyncio.to_thread(llm_service.match_jobs, cv),
        )

        await mongo_service.save_analysis(
            db,
            candidate_id,
            extracted_profile=cv.model_dump(),
            improvements=[improvement.model_dump() for improvement in improvements.improvements],
            job_matches=[match.model_dump() for match in jobs.matches],
        )
    except Exception:
        # Deliberately not re-raised: an unhandled exception inside a
        # FastAPI BackgroundTask has server-dependent (and, per TestClient,
        # actively test-breaking) propagation behavior - logging is the
        # reliable way to preserve visibility without depending on it.
        logger.exception("Analysis pipeline failed for candidate %s", candidate_id)
        await mongo_service.update_candidate_status(db, candidate_id, "failed")
