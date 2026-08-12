# 4. Data Models (MongoDB)

These are **persistence** models — they define what actually gets written to
MongoDB. Don't confuse them with the LLM output schemas in
[05-llm-schemas.md](05-llm-schemas.md); a candidate document exists in the DB the
moment a file is uploaded, before any LLM has run.

## `Candidate` — `app/models/candidate.py`

```python
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
```

One document per uploaded CV. Key fields:

- `full_name` is `Optional`, not required, even though every candidate
  obviously *has* a name. This was a mismatch caught during implementation:
  `POST /cv/upload` creates the `Candidate` document immediately, before the
  LLM has extracted anything (see [07-api-endpoints.md](07-api-endpoints.md)) —
  at creation time, nothing is known about the candidate except the uploaded
  file. `full_name`/`email` get filled in by `mongo_service.save_analysis`
  once extraction completes, pulled from `extracted_profile`. A required field
  with nothing to populate it at insert time would either force a placeholder
  value or fail validation on every upload — Optional here reflects the
  document's real lifecycle (sparse → filled in), not a schema oversight.
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
  `populate_by_name=True` is what allows constructing the model with *either*
  name.
- `model_config = ConfigDict(...)` rather than a nested `class Config:` —
  Pydantic v2's current syntax; the old class-based form still works but is
  deprecated and prints a warning on every import.

## `Analysis` — `app/models/analysis.py`

```python
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
```

(`id`/`alias="_id"` was added for the same reason as `Candidate.id` above —
every Mongo document needs its own id round-tripped back out, not just
implied by `candidate_id`. `datetime.now(timezone.utc)` rather than
`datetime.utcnow()` throughout this project's date handling — the latter is
deprecated as of Python 3.12 in favor of timezone-aware datetimes.)

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

**`AsyncIOMotorClient(..., tz_aware=True)`** — caught while implementing
`app/deps.py`: by default, PyMongo/Motor deserialize BSON UTC datetimes back
into *naive* Python `datetime` objects (correct value, but `tzinfo=None`) —
inconsistent with this project's models, which construct
`datetime.now(timezone.utc)` (timezone-*aware*) at insert time. Without
`tz_aware=True` on the client, a `Candidate.uploaded_at` you just created and
one you fetched back from the same document would compare unequal / behave
differently under `<`/`>` comparisons, purely because one has `tzinfo` set and
the other doesn't — the kind of bug that only shows up later, intermittently,
once code starts comparing timestamps. Setting it once on the client fixes it
for every read.

See [16-concepts-glossary.md](16-concepts-glossary.md) for: ObjectId, async/await,
event loop.
