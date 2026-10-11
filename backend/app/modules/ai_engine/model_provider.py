"""Replaceable Small Language Model (SLM) Provider interface and implementations."""

import abc
import json
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import (
    MalformedModelResponseError,
    ModelProviderError,
    ModelTimeoutError,
    ModelUnavailableError,
)


@dataclass
class ModelResponse:
    """Standardized output structure from a language model inference call."""

    text: str
    model_name: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    is_mock: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseLanguageModelProvider(abc.ABC):
    """Abstract interface for bounded language model providers."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abc.abstractmethod
    async def generate_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> ModelResponse:
        """Execute bounded inference and return a standardized ModelResponse."""


class DeterministicMockLanguageModelProvider(BaseLanguageModelProvider):
    """Deterministic in-memory mock provider for reproducible testing without external services."""

    def __init__(
        self,
        model_name: str = "mock-slm",
        custom_responses: dict[str, str] | None = None,
    ):
        super().__init__(model_name=model_name)
        self.custom_responses = custom_responses or {}

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> ModelResponse:
        # Check custom canned responses
        for trigger, resp in self.custom_responses.items():
            if trigger.lower() in prompt.lower():
                return ModelResponse(
                    text=resp,
                    model_name=self.model_name,
                    prompt_tokens=max(1, len(prompt) // 4),
                    completion_tokens=max(1, len(resp) // 4),
                    is_mock=True,
                )

        # Handle abstention instruction in prompt
        if "ABSTAIN" in prompt or "no relevant material" in prompt.lower():
            text = (
                "I do not have sufficient information in the official course materials to "
                "answer this question. In accordance with course guidelines, I am abstaining "
                "from speculating."
            )
            return ModelResponse(
                text=text,
                model_name=self.model_name,
                prompt_tokens=max(1, len(prompt) // 4),
                completion_tokens=max(1, len(text) // 4),
                is_mock=True,
            )

        # Extract citations if present in prompt: e.g. [Lecture: file.pdf, Page 1]
        citations = re.findall(r"\[Lecture:[^\]]+\]", prompt)
        citation_str = " ".join(dict.fromkeys(citations)) if citations else "[Course Notes]"

        # Handle Revisor audit requests
        if (
            system_prompt and "revisor" in system_prompt.lower()
        ) or "instructions for audit report" in prompt.lower():
            cand_m = re.search(
                r"CANDIDATE TEXT UNDER REVIEW:\s*(.*?)(?=\nINSTRUCTIONS|$)",
                prompt,
                re.DOTALL | re.IGNORECASE,
            )
            cand_text = cand_m.group(1).lower() if cand_m else prompt.lower()

            if (
                "quantum" in cand_text
                or "6nf" in cand_text
                or "hallucination" in cand_text
                or "unsupported" in cand_text
            ):
                status_str = "UNGROUNDED_CLAIM_DETECTED"
                summary_str = "Detected ungrounded assertions absent from provided course excerpts."
                fi_str = (
                    "- Candidate text references external concepts not substantiated by "
                    "syllabus excerpts."
                )
            elif "contradiction" in cand_text or "wrong" in cand_text or "false" in cand_text:
                status_str = "CONTRADICTION_DETECTED"
                summary_str = "Candidate text directly contradicts official course materials."
                fi_str = "- Candidate text states rules contrary to the provided lecture excerpts."
            else:
                status_str = "VERIFIED_GROUNDED"
                summary_str = (
                    "Candidate text is fully consistent with verified course excerpts "
                    f"{citation_str}."
                )
                fi_str = "None"

            text = (
                f"STATUS: {status_str}\n"
                f"SUMMARY: {summary_str}\n"
                "VERIFIED POINTS:\n"
                f"- Grounded assertions match course excerpts {citation_str}.\n"
                "FLAGGED ISSUES:\n"
                f"{fi_str}\n"
                "SUGGESTED REVISION:\n"
                f"Based on {citation_str}, concepts are verified as documented in lectures."
            )
            return ModelResponse(
                text=text,
                model_name=self.model_name,
                prompt_tokens=max(1, len(prompt) // 4),
                completion_tokens=max(1, len(text) // 4),
                is_mock=True,
            )

        # Generate a structured, syllabus-grounded pedagogical explanation
        if "armstrong" in prompt.lower() or "functional dependenc" in prompt.lower():
            text = (
                f"Based on your course materials {citation_str}, functional dependencies "
                "represent integrity constraints where attributes uniquely determine "
                "other attributes. Armstrong's Axioms consist of three primary inference rules: "
                "Reflexivity (if Y is a subset of X, then X -> Y), Augmentation (if X -> Y, "
                "then XZ -> YZ), and Transitivity (if X -> Y and Y -> Z, then X -> Z). "
                "These axioms are sound and complete for computing attribute closures "
                f"{citation_str}."
            )
        elif "normal form" in prompt.lower() or "bcnf" in prompt.lower():
            text = (
                f"According to the course lectures {citation_str}, Boyce-Codd Normal Form (BCNF) "
                "requires that for every non-trivial functional dependency X -> Y, X must be a "
                "superkey. This eliminates redundant data and update anomalies."
            )
        else:
            # General grounded synthesis echoing the context
            text = (
                f"Based on your verified course materials {citation_str}, here is the explanation: "
                "The core principles outlined in the syllabus directly address this question "
                f"with verified academic provenance {citation_str}."
            )

        return ModelResponse(
            text=text,
            model_name=self.model_name,
            prompt_tokens=max(1, len(prompt) // 4),
            completion_tokens=max(1, len(text) // 4),
            is_mock=True,
        )


class OllamaLanguageModelProvider(BaseLanguageModelProvider):
    """Production provider integrating with a local Ollama SLM endpoint."""

    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        model_name: str = settings.PRIMARY_MODEL,
        timeout_seconds: float = settings.LLM_TIMEOUT_SECONDS,
    ):
        super().__init__(model_name=model_name)
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> ModelResponse:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": min(max_tokens, 450),
                "repeat_penalty": 1.25,
                "stop": [
                    "OFFICIAL COURSE EXCERPTS:",
                    "--- EXCERPT",
                    "\nSTUDENT QUESTION:",
                    "Copyright ©",
                ],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise ModelTimeoutError(self.timeout_seconds) from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise ModelUnavailableError(self.model_name) from exc
        except Exception as exc:
            raise ModelProviderError(f"Network error communicating with Ollama: {exc}") from exc

        if response.status_code == 404:
            raise ModelUnavailableError(
                f"Model '{self.model_name}' or endpoint not found on Ollama server."
            )
        if response.status_code != 200:
            raise ModelProviderError(
                f"Ollama server returned error HTTP {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise MalformedModelResponseError("Failed to decode JSON from Ollama server.") from exc

        if not isinstance(data, dict) or "response" not in data:
            raise MalformedModelResponseError("Missing 'response' attribute in Ollama response.")

        raw_text = data.get("response")
        if raw_text is None or not str(raw_text).strip():
            raise MalformedModelResponseError("Ollama returned an empty response text.")

        return ModelResponse(
            text=str(raw_text).strip(),
            model_name=self.model_name,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            is_mock=False,
            metadata={
                "done": data.get("done", True),
                "total_duration": data.get("total_duration"),
                "load_duration": data.get("load_duration"),
            },
        )


def get_model_provider(
    use_mock: bool | None = None,
    model_name: str | None = None,
    base_url: str | None = None,
    timeout_seconds: float | None = None,
) -> BaseLanguageModelProvider:
    """Factory creating the appropriate language model provider based on runtime settings."""
    if use_mock is None:
        use_mock = settings.USE_MOCK_LLM

    if use_mock:
        return DeterministicMockLanguageModelProvider(
            model_name=model_name or "mock-slm",
        )

    return OllamaLanguageModelProvider(
        base_url=base_url or settings.OLLAMA_BASE_URL,
        model_name=model_name or settings.PRIMARY_MODEL,
        timeout_seconds=(
            timeout_seconds if timeout_seconds is not None else settings.LLM_TIMEOUT_SECONDS
        ),
    )
