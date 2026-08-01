"""
LLM provider abstraction.

Every service in this pipeline (extraction, explanation, severity) talks
to `LLMProvider.complete_json(...)`, never to a specific vendor SDK
directly. That's what makes "OpenAI GPT / Claude / Gemini, interchangeable"
from the spec an actual architectural property instead of a wish — adding
Gemini later means writing one new class, not touching the pipeline.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod

from app.core.config import get_settings

settings = get_settings()


class LLMProvider(ABC):
    @abstractmethod
    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Call the model and return a parsed JSON dict.

        Callers are responsible for validating the returned dict against
        their own Pydantic schema — this layer only guarantees valid JSON,
        not schema conformance.
        """
        raise NotImplementedError

    @abstractmethod
    def complete_text(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> str:
        """Call the model for a plain-text (non-JSON) response, e.g. chat.

        messages is a list of {"role": "user"|"assistant", "content": str},
        already in the target model's expected order.
        """
        raise NotImplementedError


class AnthropicProvider(LLMProvider):
    def __init__(self) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.LLM_MODEL

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4000,
            system=system_prompt
            + "\n\nRespond ONLY with valid JSON. No prose, no markdown fences.",
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        return _safe_json_parse(raw_text)

    def complete_text(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )
        return "".join(
            block.text for block in response.content if block.type == "text"
        )
    def __init__(self) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.LLM_MODEL

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        response = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw_text = response.choices[0].message.content
        return _safe_json_parse(raw_text)

    def complete_text(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        return response.choices[0].message.content or ""


def _safe_json_parse(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM did not return valid JSON: {exc}\nRaw: {raw_text[:500]}")


def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "openai":
        return OpenAIProvider()
    return AnthropicProvider()
