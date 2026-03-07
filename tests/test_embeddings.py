"""Tests for the pluggable embedding provider abstraction."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.embeddings import (
    EmbeddingProvider,
    OpenAIProvider,
    SentenceTransformerProvider,
    embed_texts,
    get_embedder,
)


class TestEmbeddingProviderABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            EmbeddingProvider()


class TestSentenceTransformerProvider:
    @patch("sentence_transformers.SentenceTransformer")
    def test_embed_texts_returns_list(self, MockST):
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_model.get_sentence_embedding_dimension.return_value = 2
        MockST.return_value = mock_model

        provider = SentenceTransformerProvider("test-model")
        result = provider.embed_texts(["hello", "world"])

        assert len(result) == 2
        assert isinstance(result[0], list)
        assert provider.get_dimension() == 2

    @patch("sentence_transformers.SentenceTransformer")
    def test_normalizes_embeddings(self, MockST):
        mock_model = MagicMock()
        MockST.return_value = mock_model

        provider = SentenceTransformerProvider("test-model")
        provider.embed_texts(["test"])

        mock_model.encode.assert_called_once_with(["test"], normalize_embeddings=True)


class TestOpenAIProvider:
    @patch("openai.OpenAI")
    def test_embed_texts_calls_openai(self, MockOpenAI):
        mock_client = MagicMock()
        embedding_item = MagicMock()
        embedding_item.embedding = [0.1, 0.2, 0.3]
        mock_client.embeddings.create.return_value = MagicMock(data=[embedding_item])
        MockOpenAI.return_value = mock_client

        provider = OpenAIProvider(
            api_key="test-key", model="text-embedding-3-small", dimension=3
        )
        result = provider.embed_texts(["hello"])

        assert result == [[0.1, 0.2, 0.3]]
        assert provider.get_dimension() == 3
        mock_client.embeddings.create.assert_called_once_with(
            input=["hello"], model="text-embedding-3-small"
        )


class TestGetEmbedder:
    @patch("sentence_transformers.SentenceTransformer")
    def test_default_returns_sentence_transformer(self, MockST, monkeypatch):
        get_embedder.cache_clear()
        monkeypatch.setattr(
            "app.services.embeddings.settings.embedding_provider", "sentence-transformers"
        )
        embedder = get_embedder()
        assert isinstance(embedder, SentenceTransformerProvider)
        get_embedder.cache_clear()

    def test_openai_requires_api_key(self, monkeypatch):
        get_embedder.cache_clear()
        monkeypatch.setattr(
            "app.services.embeddings.settings.embedding_provider", "openai"
        )
        monkeypatch.setattr("app.services.embeddings.settings.openai_api_key", "")
        with pytest.raises(ValueError, match="APP_OPENAI_API_KEY"):
            get_embedder()
        get_embedder.cache_clear()

    @patch("openai.OpenAI")
    def test_openai_provider_created_with_key(self, MockOpenAI, monkeypatch):
        get_embedder.cache_clear()
        monkeypatch.setattr(
            "app.services.embeddings.settings.embedding_provider", "openai"
        )
        monkeypatch.setattr(
            "app.services.embeddings.settings.openai_api_key", "sk-test"
        )
        monkeypatch.setattr(
            "app.services.embeddings.settings.openai_embedding_model",
            "text-embedding-3-small",
        )
        monkeypatch.setattr(
            "app.services.embeddings.settings.embedding_dimension", 1536
        )
        embedder = get_embedder()
        assert isinstance(embedder, OpenAIProvider)
        assert embedder.get_dimension() == 1536
        get_embedder.cache_clear()


class TestEmbedTextsFunction:
    @patch("sentence_transformers.SentenceTransformer")
    def test_embed_texts_delegates_to_provider(self, MockST, monkeypatch):
        get_embedder.cache_clear()
        monkeypatch.setattr("app.services.embeddings.settings.embedding_provider", "sentence-transformers")
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2]])
        MockST.return_value = mock_model

        result = embed_texts(["hello"])
        assert len(result) == 1
        get_embedder.cache_clear()
