# 2. Architecture

## Request flow

```
Frontend                Application         Elastic Beanstalk (EC2 ASG)         MongoDB           AWS S3
React (S3 + CloudFront)  Load Balancer       FastAPI app (Uvicorn/Gunicorn)     (candidates,      (raw CV
      |                       |              - /auth (API key middleware)       analyses,         files)
      | HTTPS                 |              - /cv/upload                      jobs cache)           |
      | (API Key header)      |              - /cv/{id}/analysis                  |                  |
      +---------------------->|              - /jobs/recommendations              |                  |
                              +-------------->|                                   |                  |
                                              |---------------------------------->|                  |
                                              |------------------------------------------------------>
                                              |
                                              v
                                        LangChain Pipeline (Pydantic schemas)
                                        - Extract CV data
                                        - Suggest edits
                                        - Match job roles
                                              |
                                              v
                                        OpenAI GPT-4o / Gemini 1.5 Pro
                                        (multimodal: reads PDF page images directly)
```

## Why the pipeline runs where it does

The FastAPI app is the only thing that talks to MongoDB, S3, and the LLM providers
directly. The frontend never touches AWS credentials or LLM API keys — it only ever
calls the backend's REST API with an `x-api-key` header. This is the standard
"thin client, fat backend" shape, and it's *why* API-key auth (not per-provider
keys shipped to the browser) matters: the LLM keys must never leave the server.

## The upload → analysis flow, end to end

1. Frontend `POST /cv/upload` with the raw file (multipart/form-data).
2. Backend uploads the raw bytes to S3 (`s3_service.upload_file`), gets back an
   S3 key, and creates a `Candidate` document in MongoDB with `status: "processing"`.
3. Backend **immediately returns** `{"candidate_id": ..., "status": "processing"}` —
   it does not make the caller wait for the LLM. The actual analysis runs as a
   FastAPI `BackgroundTask` (see [07-api-endpoints.md](07-api-endpoints.md)).
4. In the background: the raw file (PDF/DOCX/image) is normalized into page
   images (`app/utils/file_parsing.to_image_bytes` — returns `list[bytes]`,
   one PNG per page, since a real CV can span several pages; a single image
   upload comes back as a one-element list). PDFs go through `pdf2image`
   directly; DOCX files are first converted to PDF via headless LibreOffice
   (`soffice --headless --convert-to pdf`), then through the same PDF path —
   this is what makes the *multimodal* LLM call possible: the model reads the
   CV visually, no text extraction/OCR library needed.
5. Those page images go to the LLM via `llm_service.extract_cv_from_file`,
   which forces the response into the `ExtractedCV` Pydantic schema. (Not yet
   built at this point in the roadmap — `extract_cv_from_file`'s signature in
   [06-langchain-pipeline.md](06-langchain-pipeline.md) currently takes a
   single `file_bytes: bytes`; since page normalization now returns a *list*,
   that function will need to send one `image_url` content block per page in
   the `HumanMessage`, not just one. Flagged here so it isn't missed when
   Milestone 6 is built.)
6. The extracted CV is fed into two more LLM calls: `generate_improvements` (→
   `ImprovementReport`) and `match_jobs` (→ `JobMatchReport`).
7. All three results are saved to the `Analysis` collection in Mongo, keyed by
   `candidate_id`, and `Candidate.status` flips to `"analyzed"`.
8. Frontend polls `GET /cv/{candidate_id}` until `status === "analyzed"`, then
   fetches `GET /cv/{candidate_id}/analysis` to render results.

This request/poll pattern (rather than making the client wait on one long HTTP
request) exists because a 3-call LLM pipeline over a full CV can easily take
10-30+ seconds — well past what you want blocking a single HTTP request/load
balancer connection.

## Where secrets live

AWS Secrets Manager stores `OPENAI_API_KEY`, `GEMINI_API_KEY`, `MONGODB_URI`,
`API_KEY_SALT`, `AWS_S3_BUCKET` as one JSON blob per environment
(`cv-recommender/{env}/app-secrets`). These get injected into the Elastic
Beanstalk EC2 instance's environment at **boot time**, via a container command in
`.ebextensions/` that runs a small `boto3` script
(see [11-aws-infrastructure.md](11-aws-infrastructure.md#112-secrets-manager)) —
not baked into the Docker image, and not stored as plain EB environment
properties (which are visible in the AWS console to anyone with read access to
the EB application).

See [16-concepts-glossary.md](16-concepts-glossary.md) for: multimodal LLM,
background task, load balancer, Secrets Manager.
