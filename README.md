# CV Recommender

A backend service that accepts a candidate's CV (PDF/DOCX/image), extracts
structured data using a multimodal LLM, suggests concrete improvements, and
recommends relevant jobs with real search/learning links — built on FastAPI,
LangChain + Pydantic, MongoDB, and deployed on AWS (Elastic Beanstalk, S3,
CloudFront) with GitHub Actions CI/CD.

Status: **planning / not yet implemented.** Development hasn't started —
see [docs/](docs/00-index.md) for the full design doc and build roadmap.

## Docs

Start at [docs/00-index.md](docs/00-index.md). It's a reading-order index into
16 docs covering architecture, data models, the LLM pipeline, API surface,
AWS infrastructure, CI/CD, and a suggested build order
([docs/15-roadmap.md](docs/15-roadmap.md)), plus a
[concepts glossary](docs/16-concepts-glossary.md) explaining every
non-obvious term used throughout.

The original spec this is based on: [python_cv_recommender.pdf](python_cv_recommender.pdf).
