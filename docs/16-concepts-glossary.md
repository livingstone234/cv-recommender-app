# 16. Concepts Glossary

Every term flagged with a "see glossary" note across docs 01-15, in one place,
alphabetically. If you can explain each of these in your own words, you can
explain this project.

**ACM (AWS Certificate Manager)** — issues and auto-renews free TLS/SSL
certificates for AWS resources. Used here on the ALB (backend HTTPS) and
CloudFront (frontend HTTPS).

**Async / await** — Python's syntax for cooperative concurrency: an `async def`
function can `await` a slow operation (a DB call, an HTTP request) and let
other work run on the same thread while it waits, instead of blocking. FastAPI
and Motor are built around this; it's why the DB driver choice in
[04-data-models.md](04-data-models.md) matters.

**Auto Scaling Group (ASG)** — a set of EC2 instances AWS automatically grows
or shrinks based on a metric (here, CPU > 60%) and a min/max bound. Elastic
Beanstalk creates and manages one for you.

**Background task** — in FastAPI, work scheduled via `BackgroundTasks` that
runs *after* the HTTP response has already been sent, in the same process.
Cheap and simple, but not durable (if the process dies mid-task, the task is
lost) or distributed across instances — see the scaling note in
[07-api-endpoints.md](07-api-endpoints.md).

**boto3** — AWS's official Python SDK. Every direct AWS API call in this
project (S3 upload, presigned URLs, Secrets Manager reads) goes through it.

**Cache invalidation** — telling a CDN (CloudFront) to discard its cached
copies of specific files so the next request re-fetches fresh ones from the
origin (S3). Necessary after every frontend deploy — see
[13-frontend.md](13-frontend.md).

**CDN (Content Delivery Network)** — a network of geographically distributed
edge servers that cache and serve content close to the requesting user.
CloudFront is AWS's CDN.

**CI/CD gate** — a pipeline step configured to block progress (deployment)
unless a condition (tests passing, coverage threshold) is met. See
[12-cicd.md](12-cicd.md) for how this project enforces its 80% coverage rule.

**CodeBuild** — AWS's managed build service; runs a defined set of shell
commands (here: `docker build`, `pytest`, push to ECR) in a container, as one
stage of a CodePipeline.

**Dependency injection (FastAPI)** — declaring a shared piece of setup (a DB
connection, an auth check) once as a function, then attaching it to routes via
`Depends(...)`, rather than re-writing that setup inside every route handler.
See `require_api_key` and `get_db` throughout [07-api-endpoints.md](07-api-endpoints.md)
and [08-authentication.md](08-authentication.md).

**Docker** — packages an application plus everything it needs to run (system
libraries, Python version, dependencies) into a single portable image, so "it
works on my machine" also means it works in Elastic Beanstalk's Amazon Linux
container.

**ECR (Elastic Container Registry)** — AWS's private Docker image registry;
CodeBuild pushes the built image here, Elastic Beanstalk pulls from here.

**Elastic Beanstalk (EB)** — see [11-aws-infrastructure.md](11-aws-infrastructure.md#113-elastic-beanstalk-backend)
for the full explanation; in short, a managed layer over EC2/ASG/ALB that
handles provisioning and rolling deploys from a Docker image or app bundle.

**Event loop** — the single-threaded scheduler underneath Python's `asyncio`
that runs all your `async` code, switching between tasks whenever one hits an
`await`. A blocking (non-async) call inside an async route freezes the entire
event loop, not just that one request — which is the reason Motor (async)
is used instead of plain PyMongo (blocking) in this project.

**HMAC** — Hash-based Message Authentication Code; `hmac.compare_digest` uses
this family of algorithms to compare two strings in constant time, closing the
timing-attack side channel that Python's plain `==` leaves open. See
[08-authentication.md](08-authentication.md).

**IAM role / policy** — AWS's permission system. A *role* is an identity
something (an EC2 instance, a GitHub Actions run) can assume; a *policy* is the
JSON document defining exactly which AWS API actions that role may call, on
which resources. "Scoped to this ARN only" (as in
[11-aws-infrastructure.md](11-aws-infrastructure.md#112-secrets-manager)) means
the policy names one specific resource rather than granting blanket access.

**JSON mode / tool calling** — the underlying provider feature (OpenAI,
Google) that LangChain's `.with_structured_output()` uses to constrain an
LLM's response to match a given schema at generation time, rather than just
hoping the model's free-text output happens to parse as valid JSON afterward.

**LCEL (LangChain Expression Language) / Runnable** — LangChain's `prompt |
llm` composition syntax. Both objects implement a common `Runnable` interface
with `.invoke()`, and Python's `__or__` operator (`|`) is overloaded to chain
them into a pipeline. See [06-langchain-pipeline.md](06-langchain-pipeline.md).

**Load balancer** — a layer that distributes incoming requests across multiple
backend instances and stops routing to any instance that fails a health check.
This project's is an AWS **Application Load Balancer (ALB)** — see
[11-aws-infrastructure.md](11-aws-infrastructure.md#114-application-load-balancer).

**Mocking / patching** — in tests, replacing a real dependency (an AWS SDK
call, an LLM client) with a fake stand-in that returns a controlled value,
so the test exercises *your* logic without depending on a real network call.
`unittest.mock.patch` is the standard library tool for this in Python.

**MongoDB / document database** — a database that stores data as JSON-like
documents (rather than rows in fixed-schema tables), which fits this project's
naturally nested data (a CV's experience list, education list, etc.) without
needing joins across multiple tables.

**Multimodal (LLM)** — a model that accepts more than one input type in the
same request — here, text *and* images together. This is what lets
`extract_cv_from_file` send the LLM raw page images of a CV directly, instead
of running a separate OCR/text-extraction step first.

**Multipart/form-data** — the HTTP encoding used for file uploads (as opposed
to `application/json`); FastAPI's `UploadFile`/`File(...)` and the
`python-multipart` package handle parsing it.

**NAT gateway** — lets resources in a private subnet (no public IP, not
directly reachable from the internet) initiate *outbound* connections to the
internet, without being reachable inbound. Needed here so EC2 instances can
call OpenAI/Gemini's APIs while staying otherwise unreachable — see
[11-aws-infrastructure.md](11-aws-infrastructure.md#115-ec2).

**ObjectId** — MongoDB's native 12-byte primary key type, auto-generated per
document as `_id` unless you specify otherwise.

**OIDC (OpenID Connect)** — an identity federation protocol; GitHub Actions
uses it to let a workflow run assume a scoped, temporary AWS IAM role without
storing long-lived AWS credentials as a repo secret. See
[12-cicd.md](12-cicd.md).

**Origin Access Control (OAC)** — the CloudFront feature that lets a
distribution be the *only* thing allowed to read from its origin S3 bucket,
so the bucket itself can stay fully private. See
[13-frontend.md](13-frontend.md).

**Presigned URL** — a time-limited, signed URL granting temporary access to
one specific private S3 object/action, without requiring the requester to have
AWS credentials of their own. See [09-s3-storage.md](09-s3-storage.md).

**Pydantic** — Python's data-validation library: declare a schema as a class
with typed fields, and get either a validated object or a clear error.
Python's rough equivalent of TypeScript's Zod. Two distinct uses in this
project: persistence models ([04-data-models.md](04-data-models.md)) and LLM
output schemas ([05-llm-schemas.md](05-llm-schemas.md)) — same library, two
different jobs.

**pydantic-settings** — the companion library that loads a Pydantic model's
fields from environment variables / `.env` at startup, used for `app/config.py`
(see [14-environment-and-requirements.md](14-environment-and-requirements.md)).

**S3 object key** — the "path" (really a flat string identifier) an object is
stored under in an S3 bucket, e.g. `cvs/<uuid>-resume.pdf`. Not a real
filesystem path — S3 has no folders, only key prefixes that *look* like them.

**SPA (Single-Page Application)** — a frontend that loads one HTML shell and
renders everything client-side via JavaScript, rather than the server
returning a new full HTML page per navigation. The React frontend here is one.

**Structured output** — the general technique (of which Pydantic +
LangChain's `.with_structured_output()` is this project's specific
implementation) of constraining an LLM to return data matching a defined
schema, rather than free-form text you'd have to parse defensively. See
[05-llm-schemas.md](05-llm-schemas.md).

**Temperature** — an LLM sampling parameter controlling randomness;
`temperature=0` makes output as deterministic/repeatable as the model allows,
appropriate for an extraction task where you want the same CV to produce
(close to) the same structured result every time, not creative variation.

**Test fixture** — reusable setup/data for tests (e.g.
`tests/fixtures/sample_cv.pdf`), so multiple tests can share the same known
input without duplicating it.

**Timing attack** — an attack that infers secret data (like an API key) by
measuring how long a comparison operation takes, exploiting the fact that
naive string comparison short-circuits on the first mismatched character. See
[08-authentication.md](08-authentication.md).

**Trunk-based development (branch-per-environment variant)** — here, a
simplified version where `develop` and `main` map directly to dev/prod AWS
environments, rather than long-lived feature branches. See
[12-cicd.md](12-cicd.md).

**Zod** — a TypeScript schema-validation library; referenced in
[05-llm-schemas.md](05-llm-schemas.md) as the closest JS/TS equivalent to
Pydantic, for anyone coming from that ecosystem.
