from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.api_key import require_api_key
from app.config import settings

_test_app = FastAPI()


@_test_app.get("/protected", dependencies=[Depends(require_api_key)])
async def protected() -> dict:
    return {"ok": True}


client = TestClient(_test_app)


def test_valid_api_key_allows_request(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    response = client.get("/protected", headers={"x-api-key": "test-key"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_wrong_api_key_returns_401(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    response = client.get("/protected", headers={"x-api-key": "wrong-key"})
    assert response.status_code == 401


def test_missing_api_key_returns_401(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    response = client.get("/protected")
    assert response.status_code == 401
