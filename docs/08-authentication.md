# 8. API Key Authentication

## `app/auth/api_key.py`

```python
import hmac
from typing import Optional

from fastapi import Header, HTTPException, status

from app.config import settings

async def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    if x_api_key is None or not hmac.compare_digest(x_api_key, settings.API_KEY):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
```

`x_api_key` is declared `Header(default=None)`, not `Header(...)` (required),
with an explicit `is None` check inside the function. This was a real
inconsistency in the original design: with `Header(...)`, FastAPI validates
the header's *presence* before the function body ever runs — a caller who
sends no `x-api-key` header at all gets FastAPI's automatic `422 Unprocessable
Entity`, while a caller who sends the *wrong* key gets `401` from this
function's own check. Two different status codes for what's really one
failure mode ("you're not authorized to call this"). Making the header
optional and checking for `None` explicitly means both paths converge on the
same `401`, which is the response a client should actually be able to rely on.

`require_api_key` is imported and re-exported from `app/deps.py` (alongside
`get_db`), so routers use `from app.deps import require_api_key, get_db` per
[07-api-endpoints.md](07-api-endpoints.md) — one place that assembles "the
things a route depends on," rather than routers reaching into `app/auth/`
directly.

## Why `hmac.compare_digest` instead of `x_api_key == settings.API_KEY`

Python's `==` on strings short-circuits: it returns `False` as soon as it finds
the first mismatched character, which means comparing `"abc123"` against the
correct key takes a *fractionally* different amount of time than comparing
`"xyz999"` (which differs at character 1, not character 4). Measured over enough
requests, that timing difference is a real side channel — a **timing attack**
could recover the correct key one character at a time. `hmac.compare_digest`
always takes the same amount of time regardless of where the strings diverge,
closing that channel. This is a small detail, but it's exactly the kind of thing
worth being able to explain in an interview: it shows you're not just calling a
library, you understand *why* the "obviously correct" naive comparison is a
security bug.

## Scope for this project vs. the natural extension point

For the assessment's scope, a **single shared API key** (stored in Secrets
Manager, injected as `API_KEY` — see
[11-aws-infrastructure.md](11-aws-infrastructure.md#112-secrets-manager)) is
sufficient: the frontend is the only client, so there's nothing to
distinguish between multiple callers.

The `api_clients` MongoDB collection (referenced in
[03-project-structure.md](03-project-structure.md) as future scope) is where a
real multi-tenant version would go: each row would hold a client name and a
*hashed* key (never the raw key — same principle as password storage, using
something like `bcrypt`), and `require_api_key` would hash the incoming header
and look it up rather than comparing against one hardcoded value. Not building
this now is a deliberate scope call, not an oversight — worth stating that
explicitly if this comes up when you talk about the project.

See [16-concepts-glossary.md](16-concepts-glossary.md) for: timing attack, HMAC,
FastAPI `Header` dependency.
