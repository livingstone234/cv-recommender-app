# 4. Data Models (MongoDB)

These are **persistence** models — they define what actually gets written to
MongoDB. Don't confuse them with the LLM output schemas in
[05-llm-schemas.md](05-llm-schemas.md); a candidate document exists in the DB the
moment a file is uploaded, before any LLM has run.

## `Candidate` — `app/models/candidate.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from bson import ObjectId

class Candidate(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    full_name: str
    email: Optional[str] = None
    cv_s3_key: str
    original_filename: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "processing"  # processing | analyzed | failed

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
```

One document per uploaded CV. Key fields:

- `cv_s3_key` — a *pointer*, not the file itself. The binary lives in S3
  (see [09-s3-storage.md](09-s3-storage.md)); Mongo only ever stores the key
  needed to fetch it back.
- `status` — the three-state machine that drives the frontend's polling loop
  (see [02-architecture.md](02-architecture.md#the-upload--analysis-flow-end-to-end)).
  `"failed"` exists for when the LLM call errors or returns something that fails
  Pydantic validation — the pipeline should catch that and flip status rather than
  leave a candidate stuck at `"processing"` forever.
- `alias="_id"` — MongoDB's native primary key field is `_id` (an `ObjectId`), but
  Python code shouldn't have to write `candidate["_id"]` everywhere. The alias lets
  the model expose it as `.id` while still (de)serializing to/from Mongo's `_id`.
  `populate_by_name = True` is what allows constructing the model with *either*
  name.

## `Analysis` — `app/models/analysis.py`

```python
from pydantic import BaseModel
from typing import List
from datetime import datetime

class Analysis(BaseModel):
    candidate_id: str
    extracted_profile: dict     # raw structured CV (see CVSchema)
    improvements: List[dict]    # see ImprovementSchema
    job_matches: List[dict]     # see JobMatchSchema
    created_at: datetime
```

One document per completed analysis, linked to its `Candidate` by
`candidate_id`. Notice the LLM-output fields are typed as plain `dict`/`List[dict]`
here, **not** as the strict Pydantic schemas from
[05-llm-schemas.md](05-llm-schemas.md) — that's deliberate: the strict schemas do
their validation job once, at the moment the LLM responds
(`llm.invoke(...)` → validated object), then get stored as their `.model_dump()`
dict form. Re-declaring the same strict types on the persistence model would be
redundant and would make the DB layer brittle to schema evolution (if
`ImprovementSchema` gains an optional field later, old stored `Analysis` documents
shouldn't suddenly fail to load).

## Driver: Motor vs PyMongo

The stack uses **Motor** (`motor==3.*`), the official async MongoDB driver, not
plain `pymongo`. This matters because FastAPI route handlers are `async def` —
using a blocking driver (plain PyMongo) inside an async route would block the
whole event loop on every DB call, killing concurrency. Motor's API mirrors
PyMongo's almost 1:1, just with `await` in front of calls.

See [16-concepts-glossary.md](16-concepts-glossary.md) for: ObjectId, async/await,
event loop.
