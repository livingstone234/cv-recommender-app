from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.auth.api_key import require_api_key
from app.config import settings

__all__ = ["get_db", "require_api_key"]

_client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URI, tz_aware=True)


def get_db() -> AsyncIOMotorDatabase:
    return _client[settings.MONGODB_DB_NAME]
