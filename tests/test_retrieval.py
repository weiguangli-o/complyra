"""Tests for the Qdrant retrieval service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.retrieval import (
    ensure_collection,
    get_qdrant_client,
    search_chunks,
    upsert_chunks,
)


@pytest.fixture(autouse=True)
def clear_caches():
    get_qdrant_client.cache_clear()
    yield
    get_qdrant_client.cache_clear()


@pytest.fixture()
def mock_qdrant():
    with patch("app.services.retrieval.QdrantClient") as MockQdrant:
        client = MagicMock()
        MockQdrant.return_value = client
        yield client


@pytest.fixture()
def mock_embed():
    with patch("app.services.retrieval.embed_texts") as mock_et, \
         patch("app.services.retrieval.get_embedder") as mock_ge:
        mock_provider = MagicMock()
        mock_provider.get_dimension.return_value = 384
        mock_ge.return_value = mock_provider
        mock_et.return_value = [[0.1] * 384]
        yield mock_et, mock_provider


class TestEnsureCollection:
    def test_creates_collection_when_not_exists(self, mock_qdrant, mock_embed):
        mock_qdrant.collection_exists.return_value = False
        ensure_collection()
        mock_qdrant.create_collection.assert_called_once()

    def test_skips_creation_when_exists_same_dim(self, mock_qdrant, mock_embed):
        mock_qdrant.collection_exists.return_value = True
        mock_info = MagicMock()
        mock_info.config.params.vectors.size = 384
        mock_qdrant.get_collection.return_value = mock_info
        ensure_collection()
        mock_qdrant.create_collection.assert_not_called()

    def test_warns_on_dimension_mismatch(self, mock_qdrant, mock_embed, caplog):
        mock_qdrant.collection_exists.return_value = True
        mock_info = MagicMock()
        mock_info.config.params.vectors.size = 1536
        mock_qdrant.get_collection.return_value = mock_info
        import logging
        with caplog.at_level(logging.WARNING):
            ensure_collection()
        assert "dimension" in caplog.text.lower() or "mismatch" in caplog.text.lower() or "Recreate" in caplog.text


class TestUpsertChunks:
    def test_upsert_returns_document_id(self, mock_qdrant, mock_embed):
        mock_embed_texts, _ = mock_embed
        mock_embed_texts.return_value = [[0.1] * 384, [0.2] * 384]
        mock_qdrant.collection_exists.return_value = True
        mock_info = MagicMock()
        mock_info.config.params.vectors.size = 384
        mock_qdrant.get_collection.return_value = mock_info

        doc_id = upsert_chunks(["chunk1", "chunk2"], "test.pdf", "tenant1")
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0
        mock_qdrant.upsert.assert_called_once()

    def test_upsert_passes_tenant_id_in_payload(self, mock_qdrant, mock_embed):
        mock_embed_texts, _ = mock_embed
        mock_embed_texts.return_value = [[0.1] * 384]
        mock_qdrant.collection_exists.return_value = True
        mock_info = MagicMock()
        mock_info.config.params.vectors.size = 384
        mock_qdrant.get_collection.return_value = mock_info

        upsert_chunks(["chunk"], "file.txt", "my-tenant")
        call_args = mock_qdrant.upsert.call_args
        points = call_args[1]["points"]
        assert points[0].payload["tenant_id"] == "my-tenant"


class TestSearchChunks:
    def test_returns_matches(self, mock_qdrant, mock_embed):
        mock_qdrant.collection_exists.return_value = True
        mock_info = MagicMock()
        mock_info.config.params.vectors.size = 384
        mock_qdrant.get_collection.return_value = mock_info

        mock_result = MagicMock()
        mock_result.score = 0.95
        mock_result.payload = {"text": "hello", "source": "doc.pdf"}
        mock_response = MagicMock()
        mock_response.points = [mock_result]
        mock_qdrant.query_points.return_value = mock_response

        results = search_chunks("query", 4, "tenant1")
        assert len(results) == 1
        assert results[0] == ("hello", 0.95, "doc.pdf")

    def test_handles_empty_payload(self, mock_qdrant, mock_embed):
        mock_qdrant.collection_exists.return_value = True
        mock_info = MagicMock()
        mock_info.config.params.vectors.size = 384
        mock_qdrant.get_collection.return_value = mock_info

        mock_result = MagicMock()
        mock_result.score = 0.5
        mock_result.payload = None
        mock_response = MagicMock()
        mock_response.points = [mock_result]
        mock_qdrant.query_points.return_value = mock_response

        results = search_chunks("query", 4, "tenant1")
        assert results[0] == ("", 0.5, "")

    def test_applies_tenant_filter(self, mock_qdrant, mock_embed):
        mock_qdrant.collection_exists.return_value = True
        mock_info = MagicMock()
        mock_info.config.params.vectors.size = 384
        mock_qdrant.get_collection.return_value = mock_info
        mock_response = MagicMock()
        mock_response.points = []
        mock_qdrant.query_points.return_value = mock_response

        search_chunks("query", 4, "special-tenant")
        call_args = mock_qdrant.query_points.call_args
        query_filter = call_args[1]["query_filter"]
        assert query_filter.must[0].match.value == "special-tenant"
