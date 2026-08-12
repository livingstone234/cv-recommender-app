from pydantic import BaseModel, Field
from typing import List, Literal


class Improvement(BaseModel):
    section: str      # e.g. "Summary", "Experience - Company X"
    issue: str          # what's wrong
    suggestion: str     # concrete rewrite / fix
    priority: Literal["high", "medium", "low"]


class ImprovementReport(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    strengths: List[str]
    improvements: List[Improvement]
