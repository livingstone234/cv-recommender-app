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
mongomock-motor==0.0.*
moto[s3]==5.*
httpx==0.27.*
```

**System dependencies, not in `requirements.txt` because they're binaries,
not Python packages** — needed on any machine that runs `file_parsing.py`'s
`to_image_bytes` (local dev, Docker image, and CI):

- **`poppler-utils`** — `pdf2image` shells out to poppler's `pdftoppm`/`pdfinfo`
  binaries to rasterize PDF pages; without it installed at the OS level,
  PDF handling fails at runtime no matter how correctly `pdf2image` itself is
  installed via pip.
- **`libreoffice`** (specifically the `soffice` binary, headless) — DOCX files
  are converted to PDF via `soffice --headless --convert-to pdf` before going
  through the same PDF→image path, since there's no equivalent of `pdf2image`
  for `.docx` directly. This is a large package (LibreOffice's full engine) —
  worth knowing before it silently adds several minutes to a Docker build or
  CI run the first time it's added.

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
- **`mongomock`** / **`mongomock-motor`** — an in-memory fake MongoDB used in
  tests, so unit/integration tests don't need a real Mongo instance running.
  `mongomock` itself only fakes the synchronous PyMongo API; `mongomock-motor`
  is the thin async wrapper that matches Motor's `await`-based API, which is
  the one actually used against `app/services/mongo_service.py` (see
  [10-testing-strategy.md](10-testing-strategy.md)).
- **`httpx`** — FastAPI's `TestClient` is built on top of `httpx`, not
  `requests`; it's a direct dependency because integration tests import it.
- **`moto[s3]`** — an in-memory fake AWS used in tests (see
  [09-s3-storage.md](09-s3-storage.md)), the S3 equivalent of `mongomock` for
  Mongo. The `[s3]` extra pulls in just what's needed to mock S3, not every
  AWS service moto supports.

Pin versions with `.*` (minor-version pinning) rather than exact pins so
patch-level fixes flow in automatically, but a `pip install --upgrade` can't
silently jump you to a breaking major/minor version.

See [16-concepts-glossary.md](16-concepts-glossary.md) for: pydantic-settings,
semantic versioning / pinning.
