import pytest


@pytest.fixture(autouse=True)
def aws_test_credentials(monkeypatch):
    # Force dummy credentials for every test, regardless of what's on the
    # machine running them. boto3 needs *some* credentials to sign a request
    # before moto's mock_aws() can intercept it, and hardcoding fake ones here
    # means no test can ever accidentally reach real AWS, even if a mock_aws()
    # context is missing somewhere.
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")
