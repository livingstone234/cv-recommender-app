# 9. S3 Upload Service

## `app/services/s3_service.py`

```python
import re, uuid
from functools import lru_cache
from pathlib import PurePosixPath
import boto3
from app.config import settings

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")

@lru_cache(maxsize=1)
def _get_client():
    return boto3.client("s3", region_name=settings.AWS_REGION)

def _sanitize_filename(original_filename: str) -> str:
    name = PurePosixPath(original_filename).name or "upload"
    return _UNSAFE_FILENAME_CHARS.sub("_", name)[:200]

def upload_file(file_bytes: bytes, original_filename: str) -> str:
    key = f"cvs/{uuid.uuid4()}-{_sanitize_filename(original_filename)}"
    _get_client().put_object(Bucket=settings.S3_BUCKET, Key=key, Body=file_bytes)
    return key

def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    return _get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )
```

Two things changed from the original sketch, both caught while implementing:

- **The client is built lazily** (`_get_client()`, cached with `lru_cache`
  after its first real call), not as a module-level `s3 = boto3.client(...)`
  at import time. This turned out to matter for more than style: boto3
  resolves and *permanently caches* credentials the first time a given client
  instance makes a real API call — succeed or fail. A client built at import
  time (before test fixtures or a `moto` mock have set anything up) gets
  stuck with "no credentials found" forever, even after the environment is
  fixed afterward. Building it lazily means its first real use happens inside
  a request/test, after setup has actually run.
- **`_sanitize_filename` is now implemented**, not just described as a
  should-do — see the security note below, which used to just flag the gap.

## Why raw files go to S3 and not MongoDB

Storing a binary blob in a document DB works, technically, but it's the wrong
tool: it bloats document size (MongoDB has a 16MB document limit — a large,
multi-page scanned CV image could approach that), makes backups/replication
heavier for no benefit, and mixes two very different access patterns (structured
queries on candidate metadata vs. streaming a big binary file) into one
datastore. S3 is purpose-built for the latter; MongoDB holds only the pointer
(`cv_s3_key`).

## Why the S3 key includes a UUID prefix

`f"cvs/{uuid.uuid4()}-{original_filename}"` guarantees uniqueness even if two
candidates upload files named `resume.pdf` on the same day — without the UUID,
the second upload would silently overwrite the first's S3 object. It also
avoids needing to sanitize `original_filename` into a "safe" key on its own,
since the UUID prefix already makes collisions a non-issue (though the filename
portion should still be handled carefully — see security note below).

## Presigned URLs — why they exist and how they're used

`get_presigned_url` generates a temporary, signed URL that grants time-limited
access (`expires_in`, default 1 hour) to a *private* S3 object, without making
the bucket or object public and without requiring the caller to have AWS
credentials of their own. This is the standard pattern for "let the frontend
download this exact file" without ever handing out real AWS access — the
frontend gets a URL good for one object, one action (`get_object`), one hour.

This project's bucket has **block all public access** enabled (see
[11-aws-infrastructure.md](11-aws-infrastructure.md#111-s3-raw-cv-storage)), so
presigned URLs are the *only* way anything outside the backend's own AWS
credentials can ever read an uploaded CV.

## A security detail: sanitizing `original_filename`

`original_filename` comes directly from the uploader and is never trusted
verbatim. `_sanitize_filename` strips it down to its final path segment
(`PurePosixPath(...).name`, so a filename of `"../../etc/passwd"` can't smuggle
directory segments into the key), replaces anything outside
`[A-Za-z0-9._-]` with `_`, and caps it at 200 characters. Since it's only ever
used as a suffix on an S3 *key* (not a real filesystem path), the practical
risk was always low — but treating uploader-controlled input as untrusted on
principle, not "only if it turns out to matter," is the right default.

## Testing against a fake S3, not real AWS

Unit tests use **`moto`**'s `mock_aws()` context manager, which intercepts
`boto3` calls at the transport layer and serves them from an in-memory fake —
no real bucket, no network call, no AWS bill. `tests/conftest.py` adds an
**autouse** fixture that forces dummy AWS credentials
(`AWS_ACCESS_KEY_ID=testing`, etc.) for every single test in the suite,
regardless of what's actually configured on the machine running them. This
isn't just working around `boto3` needing *some* credentials to sign a
request before `moto` can intercept it (real reason it's needed) — it's also
a deliberate safety net: if a `mock_aws()` context were ever missing from a
future test, dummy credentials mean the request fails cleanly instead of
silently reaching a developer's real AWS account.

See [16-concepts-glossary.md](16-concepts-glossary.md) for: presigned URL, S3
object key, `boto3`.
