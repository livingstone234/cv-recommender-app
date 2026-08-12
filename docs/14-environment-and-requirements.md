# 14. Environment Variables & Requirements

## Environment variables

| Variable | Purpose |
|---|---|
| `MONGODB_URI` | Mongo connection string |
| `OPENAI_API_KEY` | OpenAI access |
| `GEMINI_API_KEY` | Gemini access |
| `API_KEY` | Shared API key for clients |
| `S3_BUCKET` | Raw CV storage bucket |
| `AWS_REGION` | AWS region |

All of these are read through `app/config.py` using **`pydantic-settings`**
(`BaseSettings`), not scattered `os.environ.get(...)` calls throughout the
codebase. The advantage: settings get typed and validated once, at app
startup — a missing required env var fails fast with a clear error the moment
the app boots, rather than surfacing as a confusing `NoneType has no attribute`
deep inside a request handler hours into running.

Locally, these come from a `.env` file (never committed — add it to
`.gitignore` before the first commit). In deployed environments, they're
injected via the Secrets Manager boot script described in
[11-aws-infrastructure.md](11-aws-infrastructure.md#112-secrets-manager), and in
CI they come from GitHub Actions secrets (see [12-cicd.md](12-cicd.md)).

## `requirements.txt`

```
fastapi==0.115.*
uvicorn[standard]==0.30.*
pydantic==2.*
pydantic-settings==2.*
motor==3.*                # async MongoDB driver
langchain==0.3.*
langchain-openai==0.2.*
langchain-google-genai==2.*
boto3==1.35.*
pypdf==5.*
pdf2image==1.17.*
python-multipart==0.0.*
pytest==8.*
pytest-cov==5.*
pytest-asyncio==0.24.*
mongomock==4.*
httpx==0.27.*
```

Worth knowing what a few of these are actually for, since "I listed them in
requirements.txt" isn't the same as understanding why they're there:

- **`pypdf` / `pdf2image`** — the two libraries behind `file_parsing.py`'s
  `to_image_bytes` helper (see [02-architecture.md](02-architecture.md)):
  `pypdf` for basic PDF handling, `pdf2image` for rendering PDF pages to actual
  images (it wraps the `poppler` system binary — worth remembering this needs
  `poppler-utils` installed in the Docker image, not just the pip package, or
  page rendering will fail at runtime with an unhelpful error).
- **`python-multipart`** — FastAPI needs this installed for `UploadFile`/
  `File(...)` multipart form parsing to work at all; it's easy to forget since
  nothing in your own code imports it directly.
- **`pytest-asyncio`** — required to `async def test_...()` and have pytest
  actually await it, since the FastAPI app and Motor driver are both async.
- **`mongomock`** — an in-memory fake MongoDB used in tests, so unit/integration
  tests don't need a real Mongo instance running (see
  [10-testing-strategy.md](10-testing-strategy.md)).
- **`httpx`** — FastAPI's `TestClient` is built on top of `httpx`, not
  `requests`; it's a direct dependency because integration tests import it.

Pin versions with `.*` (minor-version pinning) rather than exact pins so
patch-level fixes flow in automatically, but a `pip install --upgrade` can't
silently jump you to a breaking major/minor version.

See [16-concepts-glossary.md](16-concepts-glossary.md) for: pydantic-settings,
semantic versioning / pinning.
