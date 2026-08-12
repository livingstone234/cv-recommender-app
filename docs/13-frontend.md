# 13. Frontend — Simple UI

A minimal single-page React app (Vite + TypeScript). The frontend's whole job is
to call the backend's REST API and render its responses — it holds no business
logic, no LLM calls, no AWS credentials.

## Screens

- **Upload screen**: drag-and-drop CV, calls `POST /cv/upload`, then polls
  `GET /cv/{id}` until `status === "analyzed"`.
- **Results screen**: three tabs —
  - *Extracted Profile* (the raw `ExtractedCV` data)
  - *Improvement Report* (score + suggestions list, from `ImprovementReport`)
  - *Job Matches* (cards with match score, reasoning, clickable apply/learning
    links, from `JobMatchReport`)

## Auth from the browser

The API key is stored in a `.env` (`VITE_API_KEY`) and sent as an `x-api-key`
header via a small `axios` instance. **Worth being upfront about the
limitation here:** any value baked into a Vite/React build is visible to anyone
who opens browser devtools — a `.env`-sourced frontend API key is not a secret
in the same sense the backend's LLM provider keys are. It's sufficient for this
project's threat model (a single shared key gating a demo/assessment app, not
protecting sensitive multi-tenant data), but it's not the pattern you'd use if
the API key needed to guard something high-value — that would call for a
per-user auth flow (e.g. short-lived tokens issued after login) instead of one
static key shipped in the bundle.

## Why polling, not a websocket

The upload screen polls `GET /cv/{id}` on an interval rather than opening a
websocket/SSE connection for live updates. Given the backend's own analysis
pipeline is a `BackgroundTask` (see [07-api-endpoints.md](07-api-endpoints.md))
rather than a persistent streaming process, polling is the simpler mechanism
that matches the backend's actual capabilities — a websocket would imply the
backend can *push* a status change the moment it happens, which would require
additional infrastructure (a pub/sub layer) this project doesn't have.

## Deployment path

1. `npm run build` → static files in `dist/`.
2. **S3 bucket** `cv-recommender-frontend-{env}` (static website hosting
   **disabled**; access only via CloudFront OAC).
3. **CloudFront** distribution in front of the bucket, custom domain via ACM +
   Route 53.
4. **CodePipeline**: Source (GitHub) → Build (CodeBuild: `npm ci && npm run
   build`) → Deploy (S3 sync + CloudFront invalidation action).

**Why CloudFront + OAC instead of S3 static website hosting directly:** S3's
built-in static website hosting serves over plain HTTP and makes the bucket
itself public. Fronting the bucket with **CloudFront** (a CDN) and using
**Origin Access Control (OAC)** lets the bucket stay fully private — only
CloudFront itself can read from it — while CloudFront handles HTTPS
termination, caching at edge locations, and the custom domain. This is the
standard, secure pattern for hosting a static SPA on AWS, and it mirrors the
backend's own "load balancer in front, private resource behind" shape from
[11-aws-infrastructure.md](11-aws-infrastructure.md#115-ec2).

**Why a CloudFront invalidation is a required deploy step:** CloudFront caches
files at edge locations for performance. Without invalidating the cache after
a new deploy, users could keep being served the *previous* build's
`index.html`/JS bundle from a nearby edge cache for however long the cache TTL
is set to — the invalidation forces CloudFront to re-fetch fresh files from S3
on the next request.

See [16-concepts-glossary.md](16-concepts-glossary.md) for: CDN, Origin Access
Control, cache invalidation, SPA.
