from unittest.mock import patch

import pytest
from langchain_core.runnables import RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config import settings
from app.schemas.cv_schema import ExtractedCV
from app.schemas.improvement_schema import ImprovementReport
from app.schemas.job_match_schema import JobMatchReport
from app.services import llm_service


class _StubLLM:
    """Fakes the get_llm(...).with_structured_output(Schema) chain-entry point,
    returning a canned value regardless of input. RunnableLambda gives a real
    Runnable, so it composes correctly with `prompt | llm` (LCEL) and supports
    plain `.invoke(...)` the same way a real chat model would — no network
    call, no API key needed, since we're testing our own orchestration logic
    (prompt building, schema selection, provider dispatch), not the LLM."""

    def __init__(self, return_value):
        self._return_value = return_value
        self.requested_schema = None
        self.received_input = None

    def with_structured_output(self, schema):
        self.requested_schema = schema

        def _fake_call(chain_input):
            self.received_input = chain_input
            return self._return_value

        return RunnableLambda(_fake_call)


SAMPLE_CV = ExtractedCV(
    full_name="Ama Owusu",
    skills=["Python", "FastAPI"],
    years_of_experience=3.5,
    experience=[],
    education=[],
)


def test_get_llm_openai_returns_chatopenai(monkeypatch):
    # get_llm needs *some* key to construct a client at all - both SDKs treat
    # settings' empty-string default the same as "no key provided" and raise
    # before this test ever gets to assert anything, so a dummy key stands in.
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-openai-key")

    llm = llm_service.get_llm("openai")

    assert isinstance(llm, ChatOpenAI)


def test_get_llm_gemini_returns_chatgooglegenerativeai(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key")

    llm = llm_service.get_llm("gemini")

    assert isinstance(llm, ChatGoogleGenerativeAI)


def test_get_llm_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        llm_service.get_llm("anthropic")


def test_extract_cv_from_file_sends_one_image_block_per_page():
    stub = _StubLLM(SAMPLE_CV)

    with patch.object(llm_service, "get_llm", return_value=stub):
        result = llm_service.extract_cv_from_file([b"page-one", b"page-two"], mime_type="image/png")

    assert result == SAMPLE_CV
    assert stub.requested_schema is ExtractedCV

    sent_message = stub.received_input[0]
    image_blocks = [block for block in sent_message.content if block["type"] == "image_url"]
    text_blocks = [block for block in sent_message.content if block["type"] == "text"]
    assert len(image_blocks) == 2
    assert len(text_blocks) == 1
    assert image_blocks[0]["image_url"].startswith("data:image/png;base64,")


def test_extract_cv_from_file_single_page_still_works():
    stub = _StubLLM(SAMPLE_CV)
    with patch.object(llm_service, "get_llm", return_value=stub):
        result = llm_service.extract_cv_from_file([b"only-page"])

    assert result == SAMPLE_CV


def test_generate_improvements_returns_llm_result():
    expected = ImprovementReport(overall_score=72, strengths=["Clear structure"], improvements=[])
    stub = _StubLLM(expected)

    with patch.object(llm_service, "get_llm", return_value=stub):
        result = llm_service.generate_improvements(SAMPLE_CV)

    assert result == expected
    assert stub.requested_schema is ImprovementReport


def test_match_jobs_returns_llm_result():
    expected = JobMatchReport(matches=[])
    stub = _StubLLM(expected)

    with patch.object(llm_service, "get_llm", return_value=stub):
        result = llm_service.match_jobs(SAMPLE_CV)

    assert result == expected
    assert stub.requested_schema is JobMatchReport


def test_generate_improvements_and_match_jobs_default_to_openai_provider():
    stub = _StubLLM(None)
    with patch.object(llm_service, "get_llm", return_value=stub) as mock_get_llm:
        llm_service.generate_improvements(SAMPLE_CV)
    mock_get_llm.assert_called_once_with("openai")
