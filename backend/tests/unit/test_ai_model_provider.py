"""Unit tests for Phase 5 AI Model Providers, Ollama error handling, and prompt assembler."""

import httpx
import pytest

from app.core.errors import (
    MalformedModelResponseError,
    ModelProviderError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from app.modules.ai_engine.model_provider import (
    DeterministicMockLanguageModelProvider,
    OllamaLanguageModelProvider,
    get_model_provider,
)
from app.modules.ai_engine.tutor_engine import GroundedTutorEngine
from app.modules.knowledge_engine.retrieval_engine import RetrievalMatch


@pytest.mark.unit
async def test_mock_provider_grounded_response_with_citation() -> None:
    provider = DeterministicMockLanguageModelProvider(model_name="test-mock")
    prompt = (
        "OFFICIAL COURSE EXCERPTS:\n"
        "--- EXCERPT 1 [[Lecture: notes.pdf, Page 2]] ---\n"
        "Armstrong's Axioms consist of Reflexivity, Augmentation, and Transitivity.\n\n"
        "STUDENT QUESTION:\nExplain Armstrong's Axioms\n"
    )
    resp = await provider.generate_response(prompt=prompt)
    assert resp.is_mock
    assert "Armstrong" in resp.text
    assert "[Lecture: notes.pdf, Page 2]" in resp.text
    assert resp.prompt_tokens is not None and resp.prompt_tokens > 0
    assert resp.completion_tokens is not None and resp.completion_tokens > 0


@pytest.mark.unit
async def test_mock_provider_abstention_handling() -> None:
    provider = DeterministicMockLanguageModelProvider()
    resp = await provider.generate_response(prompt="ABSTAIN: no relevant material in syllabus")
    assert resp.is_mock
    assert "abstaining" in resp.text.lower()


@pytest.mark.unit
async def test_mock_provider_custom_responses() -> None:
    provider = DeterministicMockLanguageModelProvider(
        custom_responses={"special query": "Custom canned response for testing."}
    )
    resp = await provider.generate_response(prompt="Here is a special query for testing.")
    assert resp.text == "Custom canned response for testing."


@pytest.mark.unit
def test_get_model_provider_factory() -> None:
    mock_prov = get_model_provider(use_mock=True)
    assert isinstance(mock_prov, DeterministicMockLanguageModelProvider)

    ollama_prov = get_model_provider(use_mock=False, model_name="test-model")
    assert isinstance(ollama_prov, OllamaLanguageModelProvider)
    assert ollama_prov.model_name == "test-model"


@pytest.mark.unit
async def test_ollama_provider_successful_inference(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLanguageModelProvider(
        base_url="http://mock-ollama:11434",
        model_name="qwen2.5:3b",
        timeout_seconds=5.0,
    )

    async def mock_post(client: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
        data = {
            "model": "qwen2.5:3b",
            "response": "A functional dependency X -> Y holds when identical X implies Y.",
            "done": True,
            "prompt_eval_count": 25,
            "eval_count": 40,
        }
        return httpx.Response(status_code=200, json=data)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    resp = await provider.generate_response(prompt="What is a functional dependency?")
    assert not resp.is_mock
    assert "functional dependency" in resp.text
    assert resp.prompt_tokens == 25
    assert resp.completion_tokens == 40


@pytest.mark.unit
async def test_ollama_provider_timeout_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLanguageModelProvider(
        base_url="http://mock-ollama:11434",
        model_name="qwen2.5:3b",
        timeout_seconds=2.0,
    )

    async def mock_post(client: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
        raise httpx.ReadTimeout("Request timed out")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    with pytest.raises(ModelTimeoutError) as exc_info:
        await provider.generate_response(prompt="Slow prompt")

    assert exc_info.value.status_code == 504
    assert "2.0s" in exc_info.value.detail


@pytest.mark.unit
async def test_ollama_provider_connection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLanguageModelProvider(
        base_url="http://mock-ollama:11434",
        model_name="qwen2.5:3b",
    )

    async def mock_post(client: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    with pytest.raises(ModelUnavailableError) as exc_info:
        await provider.generate_response(prompt="Prompt")

    assert exc_info.value.status_code == 503
    assert "qwen2.5:3b" in exc_info.value.detail


@pytest.mark.unit
async def test_ollama_provider_model_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLanguageModelProvider(
        base_url="http://mock-ollama:11434",
        model_name="nonexistent:model",
    )

    async def mock_post(client: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(status_code=404, text="model 'nonexistent:model' not found")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    with pytest.raises(ModelUnavailableError) as exc_info:
        await provider.generate_response(prompt="Prompt")

    assert exc_info.value.status_code == 503


@pytest.mark.unit
async def test_ollama_provider_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLanguageModelProvider(
        base_url="http://mock-ollama:11434",
        model_name="qwen2.5:3b",
    )

    async def mock_post(client: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(status_code=500, text="Internal Ollama Crash")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    with pytest.raises(ModelProviderError) as exc_info:
        await provider.generate_response(prompt="Prompt")

    assert exc_info.value.status_code == 502


@pytest.mark.unit
async def test_ollama_provider_malformed_and_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = OllamaLanguageModelProvider(
        base_url="http://mock-ollama:11434",
        model_name="qwen2.5:3b",
    )

    # Empty text response
    async def mock_post_empty(
        client: httpx.AsyncClient, url: str, **kwargs: object
    ) -> httpx.Response:
        return httpx.Response(status_code=200, json={"model": "qwen2.5:3b", "response": "   "})

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post_empty)
    with pytest.raises(MalformedModelResponseError):
        await provider.generate_response(prompt="Prompt")

    # Missing response attribute
    async def mock_post_missing(
        client: httpx.AsyncClient, url: str, **kwargs: object
    ) -> httpx.Response:
        return httpx.Response(status_code=200, json={"model": "qwen2.5:3b", "done": True})

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post_missing)
    with pytest.raises(MalformedModelResponseError):
        await provider.generate_response(prompt="Prompt")


@pytest.mark.unit
def test_tutor_engine_context_bounding_and_citations() -> None:
    matches = [
        RetrievalMatch(
            chunk_id=f"c_{i}",
            document_id=f"doc_{i}",
            document_filename=f"lecture_{i}.pdf",
            page_number=i,
            content=f"Content excerpt for lecture {i}. " * 20,
            similarity_score=0.85,
            citation=f"[Lecture: lecture_{i}.pdf, Page {i}]",
            metadata_attributes={},
        )
        for i in range(1, 10)
    ]

    # Test bounded context limit
    assembled = GroundedTutorEngine.assemble_prompt(
        query="What is database normalization?",
        matches=matches,
        max_context_chars=400,
    )

    assert assembled.truncated
    assert assembled.total_characters > 0
    assert len(assembled.citations) >= 1
    assert "OFFICIAL COURSE EXCERPTS" in assembled.user_prompt
    assert "NON-NEGOTIABLE GROUNDING RULES" in assembled.system_prompt
