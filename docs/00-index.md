# CV Recommender — Documentation Index

This `docs/` folder is the guide we work from before and during development. It's
written so that by the time the project is built, you can explain *every* design
decision in it — in an interview, on your CV, or in a README — not just point at
code that works.

Source of truth for the raw spec: [`python_cv_recommender.pdf`](../python_cv_recommender.pdf)
at the repo root. These docs restate it in Markdown (so it's diffable and linkable)
and add the "why", which the PDF mostly leaves implicit.

## Reading order

| # | Doc | What it covers |
|---|-----|-----------------|
| 1 | [01-overview.md](01-overview.md) | The problem, the stack, why each tool was picked |
| 2 | [02-architecture.md](02-architecture.md) | Request lifecycle, the full data flow diagram |
| 3 | [03-project-structure.md](03-project-structure.md) | Folder layout and what belongs where |
| 4 | [04-data-models.md](04-data-models.md) | MongoDB persistence models (Candidate, Analysis) |
| 5 | [05-llm-schemas.md](05-llm-schemas.md) | Pydantic schemas that constrain LLM output |
| 6 | [06-langchain-pipeline.md](06-langchain-pipeline.md) | The multimodal extraction + structured-output chains |
| 7 | [07-api-endpoints.md](07-api-endpoints.md) | REST API surface, sample route walkthrough |
| 8 | [08-authentication.md](08-authentication.md) | API key auth middleware |
| 9 | [09-s3-storage.md](09-s3-storage.md) | Raw CV storage in S3 |
| 10 | [10-testing-strategy.md](10-testing-strategy.md) | Unit vs integration tests, coverage gate |
| 11 | [11-aws-infrastructure.md](11-aws-infrastructure.md) | S3, Secrets Manager, Elastic Beanstalk, ALB, EC2, CodePipeline |
| 12 | [12-cicd.md](12-cicd.md) | GitHub Actions dev/prod pipelines |
| 13 | [13-frontend.md](13-frontend.md) | The React upload/results UI and its deploy path |
| 14 | [14-environment-and-requirements.md](14-environment-and-requirements.md) | Env vars and pinned dependencies |
| 15 | [15-roadmap.md](15-roadmap.md) | Suggested build order, milestone by milestone |
| 16 | [16-concepts-glossary.md](16-concepts-glossary.md) | Every unfamiliar term, explained once, linked from everywhere |

## How to use this while building

- Before implementing a section (e.g. the LangChain service), re-read its doc.
- If a concept is unclear, check [16-concepts-glossary.md](16-concepts-glossary.md) first —
  it's written to be the thing you re-read right before an interview.
- The [15-roadmap.md](15-roadmap.md) is the actual order we'll build in — it's not the
  same as the PDF's section order, because the PDF documents the *finished* system,
  not the order you'd sanely build it in (e.g. auth and tests come before AWS).
- When something in these docs turns out to be wrong once we're actually coding
  (it will), update the doc in the same commit as the code change. Docs that drift
  from reality are worse than no docs.
