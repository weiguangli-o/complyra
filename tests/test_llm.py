"""Tests for the LLM service (Ollama integration)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.llm import (
    _build_prompt,
    ensure_model_ready,
    generate_answer,
    generate_answer_stream,
    ollama_health,
)


class TestBuildPrompt:
    def test_includes_context_and_question(self):
        prompt = _build_prompt("What is X?", ["Context A", "Context B"])
        assert "Context A" in prompt
        assert "Context B" in prompt
        assert "What is X?" in prompt
        assert "Answer:" in prompt

    def test_includes_security_guardrail(self):
        prompt = _build_prompt("q", ["c"])
        assert "untrusted data" in prompt

    def test_empty_contexts(self):
        prompt = _build_prompt("q", [])
        assert "Question: q" in prompt


@pytest.fixture(autouse=True)
def _force_ollama_provider(monkeypatch):
    """Tests in this module target the Ollama code path."""
    monkeypatch.setattr("app.services.llm.settings.llm_provider", "ollama")


class TestGenerateAnswer:
    @patch("app.services.llm.httpx.Client")
    def test_returns_stripped_response(self, MockClient):
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "  answer text  "}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        MockClient.return_value = mock_client

        result = generate_answer("question", ["context"])
        assert result == "answer text"

    @patch("app.services.llm.httpx.Client")
    def test_sends_correct_payload(self, MockClient):
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "ok"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        MockClient.return_value = mock_client

        generate_answer("q", ["c"])
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["stream"] is False
        assert "prompt" in payload

    @patch("app.services.llm.httpx.Client")
    def test_empty_response(self, MockClient):
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        MockClient.return_value = mock_client

        result = generate_answer("q", ["c"])
        assert result == ""


class _AsyncLineIterator:
    """Helper to create a proper async iterator for mocking aiter_lines."""

    def __init__(self, lines):
        self._lines = lines
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._lines):
            raise StopAsyncIteration
        line = self._lines[self._index]
        self._index += 1
        return line


class TestGenerateAnswerStream:
    @pytest.mark.asyncio
    async def test_yields_tokens(self):
        lines = [
            json.dumps({"response": "Hello", "done": False}),
            json.dumps({"response": " world", "done": True}),
        ]

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = MagicMock(return_value=_AsyncLineIterator(lines))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.llm.httpx.AsyncClient", return_value=mock_client):
            tokens = []
            async for token in generate_answer_stream("q", ["c"]):
                tokens.append(token)
            assert tokens == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_skips_empty_tokens(self):
        lines = [
            json.dumps({"response": "", "done": False}),
            json.dumps({"response": "ok", "done": True}),
        ]

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = MagicMock(return_value=_AsyncLineIterator(lines))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.llm.httpx.AsyncClient", return_value=mock_client):
            tokens = []
            async for token in generate_answer_stream("q", ["c"]):
                tokens.append(token)
            assert tokens == ["ok"]


class TestOllamaHealth:
    @patch("app.services.llm.httpx.Client")
    def test_healthy(self, MockClient):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        MockClient.return_value = mock_client

        assert ollama_health() is True

    @patch("app.services.llm.httpx.Client")
    def test_unhealthy(self, MockClient):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("connection refused")
        MockClient.return_value = mock_client

        assert ollama_health() is False


class TestEnsureModelReady:
    @patch("app.services.llm.httpx.Client")
    def test_prepull_success(self, MockClient, monkeypatch):
        monkeypatch.setattr("app.services.llm.settings.ollama_prepull", True)
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        MockClient.return_value = mock_client

        assert ensure_model_ready() is True

    @patch("app.services.llm.httpx.Client")
    def test_prepull_failure(self, MockClient, monkeypatch):
        monkeypatch.setattr("app.services.llm.settings.ollama_prepull", True)
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = Exception("timeout")
        MockClient.return_value = mock_client

        assert ensure_model_ready() is False

    def test_prepull_disabled(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.settings.ollama_prepull", False)
        assert ensure_model_ready() is True
