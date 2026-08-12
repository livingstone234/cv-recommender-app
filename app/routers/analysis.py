from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.deps import get_db, require_api_key
from app.services import mongo_service

router = APIRouter(prefix="/cv", tags=["analysis"], dependencies=[Depends(require_api_key)])


@router.get("/{candidate_id}/analysis")
async def get_analysis(candidate_id: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> dict:
    candidate = await mongo_service.get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    analysis = await mongo_service.get_analysis(db, candidate_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis not ready yet (candidate status: {candidate.status})",
        )

    return {
        "extracted_profile": analysis.extracted_profile,
        "improvements": analysis.improvements,
        "job_matches": analysis.job_matches,
    }
