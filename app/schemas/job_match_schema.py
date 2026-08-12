from pydantic import BaseModel, Field
from typing import List


class SkillGap(BaseModel):
    skill: str
    resource_name: str
    resource_url: str


class JobMatch(BaseModel):
    job_title: str
    match_score: int = Field(ge=0, le=100)
    reasoning: str
    apply_links: List[str]
    skill_gaps: List[SkillGap] = []


class JobMatchReport(BaseModel):
    matches: List[JobMatch]
