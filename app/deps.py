from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URI, tz_aware=True)


def get_db() -> AsyncIOMotorDatabase:
    return _client[settings.MONGODB_DB_NAME]
