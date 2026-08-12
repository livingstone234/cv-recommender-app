# 9. S3 Upload Service

## `app/services/s3_service.py`

```python
import boto3, uuid
from app.config import settings

s3 = boto3.client("s3", region_name=settings.AWS_REGION)

def upload_file(file_bytes: bytes, original_filename: str) -> str:
    key = f"cvs/{uuid.uuid4()}-{original_filename}"
    s3.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=file_bytes)
    return key

def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )
```

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

## A security detail worth knowing before you implement this

`original_filename` comes directly from the uploader — it should never be
trusted verbatim in a path in a way that could allow path traversal
(e.g. a filename containing `../../`) or that gets rendered somewhere unescaped.
Since it's used here only as a suffix on an S3 *key* (not a filesystem path),
the practical risk is low, but it's the kind of input worth treating as
untrusted on principle: sanitize or at minimum length-limit it before use.

See [16-concepts-glossary.md](16-concepts-glossary.md) for: presigned URL, S3
object key, `boto3`.
