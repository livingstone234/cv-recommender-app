import re
import uuid
from functools import lru_cache
from pathlib import PurePosixPath

import boto3

from app.config import settings

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")
_MAX_FILENAME_LENGTH = 200


@lru_cache(maxsize=1)
def _get_client():
    # Built lazily (on first real call), not at import time: an
    # eagerly-created module-level client resolves and caches AWS
    # credentials the moment this module is imported, which can happen
    # before test fixtures (or a moto mock_aws() context) are active —
    # making the client untestable no matter what's set up afterward.
    return boto3.client("s3", region_name=settings.AWS_REGION)


def _sanitize_filename(original_filename: str) -> str:
    # Untrusted input from the uploader: strip any path components (a client
    # could set filename to "../../etc/passwd") and collapse anything outside
    # a safe character set, so it can't smuggle path-like segments into the
    # S3 key even though S3 keys aren't real filesystem paths.
    name = PurePosixPath(original_filename).name or "upload"
    name = _UNSAFE_FILENAME_CHARS.sub("_", name)
    return name[:_MAX_FILENAME_LENGTH]


def upload_file(file_bytes: bytes, original_filename: str) -> str:
    safe_filename = _sanitize_filename(original_filename)
    key = f"cvs/{uuid.uuid4()}-{safe_filename}"
    _get_client().put_object(Bucket=settings.S3_BUCKET, Key=key, Body=file_bytes)
    return key


def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    return _get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )
