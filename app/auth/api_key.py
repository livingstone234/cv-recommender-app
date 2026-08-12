import hmac
from typing import Optional

from fastapi import Header, HTTPException, status

from app.config import settings


async def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    if x_api_key is None or not hmac.compare_digest(x_api_key, settings.API_KEY):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
