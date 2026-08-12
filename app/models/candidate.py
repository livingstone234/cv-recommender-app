from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, timezone
from typing import Optional


class Candidate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[str] = Field(default=None, alias="_id")
    full_name: Optional[str] = None
    email: Optional[str] = None
    cv_s3_key: str
    original_filename: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "processing"  # processing | analyzed | failed
