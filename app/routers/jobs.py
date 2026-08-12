from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.deps import get_db, require_api_key
from app.services import mongo_service

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(require_api_key)])


class JobRecommendationsRequest(BaseModel):
    candidate_id: str


@router.post("/recommendations")
async def get_job_recommendations(
    body: JobRecommendationsRequest, db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    analysis = await mongo_service.get_analysis(db, body.candidate_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found for this candidate")
    return {"matches": analysis.job_matches}
