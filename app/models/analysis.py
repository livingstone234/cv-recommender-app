from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime, timezone


class Analysis(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[str] = Field(default=None, alias="_id")
    candidate_id: str
    extracted_profile: dict     # raw structured CV (see CVSchema)
    improvements: List[dict]    # see ImprovementSchema
    job_matches: List[dict]     # see JobMatchSchema
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
