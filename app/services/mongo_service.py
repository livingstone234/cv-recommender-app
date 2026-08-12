from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.analysis import Analysis
from app.models.candidate import Candidate

CANDIDATES_COLLECTION = "candidates"
ANALYSES_COLLECTION = "analyses"


async def create_candidate(db: AsyncIOMotorDatabase, original_filename: str, cv_s3_key: str) -> Candidate:
    doc = {
        "original_filename": original_filename,
        "cv_s3_key": cv_s3_key,
        "full_name": None,
        "email": None,
        "uploaded_at": datetime.now(timezone.utc),
        "status": "processing",
    }
    result = await db[CANDIDATES_COLLECTION].insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return Candidate(**doc)


async def get_candidate(db: AsyncIOMotorDatabase, candidate_id: str) -> Optional[Candidate]:
    doc = await db[CANDIDATES_COLLECTION].find_one({"_id": ObjectId(candidate_id)})
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    return Candidate(**doc)


async def update_candidate_status(db: AsyncIOMotorDatabase, candidate_id: str, status: str) -> None:
    await db[CANDIDATES_COLLECTION].update_one(
        {"_id": ObjectId(candidate_id)}, {"$set": {"status": status}}
    )


async def save_analysis(
    db: AsyncIOMotorDatabase,
    candidate_id: str,
    extracted_profile: dict,
    improvements: list[dict],
    job_matches: list[dict],
) -> Analysis:
    doc = {
        "candidate_id": candidate_id,
        "extracted_profile": extracted_profile,
        "improvements": improvements,
        "job_matches": job_matches,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db[ANALYSES_COLLECTION].insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    await db[CANDIDATES_COLLECTION].update_one(
        {"_id": ObjectId(candidate_id)},
        {
            "$set": {
                "status": "analyzed",
                "full_name": extracted_profile.get("full_name"),
                "email": extracted_profile.get("email"),
            }
        },
    )
    return Analysis(**doc)


async def get_analysis(db: AsyncIOMotorDatabase, candidate_id: str) -> Optional[Analysis]:
    doc = await db[ANALYSES_COLLECTION].find_one({"candidate_id": candidate_id})
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    return Analysis(**doc)
