"""Tests for the health check endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.api.routes.health import live_check, ready_check


class TestLiveCheck:
    def test_returns_ok(self):
        result = live_check()
        assert result["status"] == "ok"


class TestReadyCheck:
    @patch("app.api.routes.health.ollama_health")
    @patch("app.api.routes.health.get_qdrant_client")
    @patch("app.api.routes.health.SessionLocal")
    def test_all_healthy(self, mock_session, mock_qdrant_fn, mock_ollama):
        # Mock DB session
        mock_db = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        # Mock Qdrant
        mock_qdrant_fn.return_value.get_collections.return_value = MagicMock()

        # Mock Ollama
        mock_ollama.return_value = True

        result = ready_check()
        assert result["status"] == "ok"
        assert result["checks"]["database"] is True
        assert result["checks"]["qdrant"] is True
        assert result["checks"]["ollama"] is True

    @patch("app.api.routes.health.ollama_health")
    @patch("app.api.routes.health.get_qdrant_client")
    @patch("app.api.routes.health.SessionLocal")
    def test_ollama_unhealthy(self, mock_session, mock_qdrant_fn, mock_ollama):
        mock_db = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_qdrant_fn.return_value.get_collections.return_value = MagicMock()
        mock_ollama.return_value = False

        result = ready_check()
        assert result["status"] == "degraded"
        assert result["checks"]["ollama"] is False

    @patch("app.api.routes.health.ollama_health")
    @patch("app.api.routes.health.get_qdrant_client")
    @patch("app.api.routes.health.SessionLocal")
    def test_db_unhealthy(self, mock_session, mock_qdrant_fn, mock_ollama):
        mock_session.return_value.__enter__ = MagicMock(
            side_effect=Exception("db down")
        )
        mock_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_qdrant_fn.return_value.get_collections.return_value = MagicMock()
        mock_ollama.return_value = True

        result = ready_check()
        assert result["status"] == "degraded"

    @patch("app.api.routes.health.ollama_health")
    @patch("app.api.routes.health.get_qdrant_client")
    @patch("app.api.routes.health.SessionLocal")
    def test_qdrant_unhealthy(self, mock_session, mock_qdrant_fn, mock_ollama):
        mock_db = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_qdrant_fn.return_value.get_collections.side_effect = Exception("qdrant down")
        mock_ollama.return_value = True

        result = ready_check()
        assert result["status"] == "degraded"
        assert result["checks"]["qdrant"] is False
