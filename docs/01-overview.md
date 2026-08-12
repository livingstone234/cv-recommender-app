# 1. Project Overview

## The problem

A candidate uploads their CV (PDF, DOCX, or an image of one). The system should:

1. **Extract** the CV's content into structured data (name, skills, experience, education...).
2. **Critique** it — a scored report with concrete, section-by-section rewrite suggestions.
3. **Recommend jobs** — the 5 best-fit roles, with real search links on job boards, and
   for any skill gaps, real links to learning resources that close them.

The interesting engineering problem isn't "call an LLM" — it's making an LLM's
notoriously unstructured output (paragraphs of prose) into something a backend can
reliably parse, store, and serve as JSON, every single time, even across two
different model providers.

## Tech stack, and why each piece is there

| Item | Choice | Why this, not the obvious alternative |
|---|---|---|
| Language | Python 3.12 | LLM/data tooling (LangChain, pypdf) is Python-first |
| API framework | FastAPI | Async-native, Pydantic-integrated, auto-generates OpenAPI docs |
| Database | MongoDB (Atlas or self-hosted) | The data is document-shaped (nested CV JSON) — forcing it into relational tables would mean constant joins for no benefit |
| LLM orchestration | LangChain, output validated with **Pydantic** | LangChain standardizes calling different providers (OpenAI, Gemini) through one interface; Pydantic is what turns "the model said some JSON" into "the model returned a typed, validated `ExtractedCV` object or raised an error" |
| LLM providers | OpenAI (`gpt-4o`) and Google Gemini (`gemini-1.5-pro`) — both multimodal | Two providers, selectable at call time, both capable of reading an *image* of a CV page directly (no OCR step needed) |
| Auth | API key (header-based) | This is a backend-to-backend / single-frontend service, not a multi-user consumer app — no need for OAuth/session complexity |
| Storage | AWS S3 (raw CV files) | Object storage is the correct place for binary files; MongoDB stores metadata + a pointer (`cv_s3_key`), not the file itself |
| Tests | Pytest (unit + integration), coverage via `pytest-cov` | Industry-standard Python testing stack |
| CI/CD | GitHub Actions — separate `dev` and `prod` pipelines | Two branches (`develop`, `main`) map to two isolated AWS environments |
| Backend hosting | AWS Elastic Beanstalk (behind an Application Load Balancer) | Managed EC2 + autoscaling + health checks without hand-rolling infra, while still being "real AWS" (not a PaaS black box like Heroku) |
| Frontend hosting | S3 + CloudFront, deployed via CodePipeline | Standard static-site pattern: cheap, CDN-backed, no server to manage |
| Secrets | AWS Secrets Manager | Keeps API keys and DB URIs out of the repo and out of plain EC2 env vars |

**If you take one thing away for your CV/portfolio**: this project demonstrates
*structured LLM output* (LangChain + Pydantic, multimodal input) and a *complete
AWS deployment* (not just "I called the OpenAI API in a script"), backed by tests
and a real CI/CD gate. That combination — LLM engineering + production infra — is
the differentiator worth calling out explicitly when you describe it.

## Non-goals (scope boundaries worth knowing, so you don't over-build)

- No user accounts / login system — a single shared API key is sufficient per the spec.
  The `api_clients` Mongo collection is scaffolded as *the* extension point if
  multi-tenant keys are ever needed, but it's not built out now.
- No real-time streaming of LLM output — the analysis runs as a background task and
  the frontend polls for status, rather than websockets/SSE.
- Job matching returns *search links* (LinkedIn/Indeed query URLs), not live scraped
  job listings — there's no job-board API integration, deliberately, to avoid
  scraping ToS issues and flaky third-party dependencies.

See [16-concepts-glossary.md](16-concepts-glossary.md) for definitions of any term
above you're not 100% sure of (Pydantic, multimodal, structured output, etc.).
