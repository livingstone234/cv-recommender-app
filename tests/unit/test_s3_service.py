import boto3
import pytest
from moto import mock_aws

from app.config import settings
from app.services import s3_service


@pytest.fixture
def s3_bucket():
    with mock_aws():
        client = boto3.client("s3", region_name=settings.AWS_REGION)
        client.create_bucket(
            Bucket=settings.S3_BUCKET,
            CreateBucketConfiguration={"LocationConstraint": settings.AWS_REGION},
        )
        yield client


def test_upload_file_stores_object_under_cvs_prefix(s3_bucket):
    key = s3_service.upload_file(b"%PDF-1.4 fake content", "resume.pdf")

    assert key.startswith("cvs/")
    assert key.endswith("-resume.pdf")

    stored = s3_bucket.get_object(Bucket=settings.S3_BUCKET, Key=key)
    assert stored["Body"].read() == b"%PDF-1.4 fake content"


def test_upload_file_two_uploads_get_distinct_keys(s3_bucket):
    key_a = s3_service.upload_file(b"a", "resume.pdf")
    key_b = s3_service.upload_file(b"b", "resume.pdf")

    assert key_a != key_b


def test_upload_file_sanitizes_path_traversal_filename(s3_bucket):
    key = s3_service.upload_file(b"data", "../../etc/passwd")

    assert "../" not in key
    assert key.endswith("-passwd")


def test_upload_file_sanitizes_unsafe_characters(s3_bucket):
    key = s3_service.upload_file(b"data", "my resume (final)!.pdf")

    assert key.endswith("-my_resume__final__.pdf")


def test_get_presigned_url_returns_a_url_for_the_key(s3_bucket):
    key = s3_service.upload_file(b"data", "resume.pdf")

    url = s3_service.get_presigned_url(key)

    assert settings.S3_BUCKET in url
    assert key in url
