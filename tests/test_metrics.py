"""Tests for the Prometheus metrics module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from starlette.responses import Response

from app.core.metrics import MetricsMiddleware, _route_path, metrics_response


class TestRoutePathExtraction:
    def test_with_route(self):
        request = MagicMock()
        route = MagicMock()
        route.path = "/api/chat/"
        request.scope = {"route": route}
        assert _route_path(request) == "/api/chat/"

    def test_without_route(self):
        request = MagicMock()
        request.scope = {}
        request.url.path = "/api/health/live"
        assert _route_path(request) == "/api/health/live"


class TestMetricsResponse:
    @patch("app.core.metrics.get_redis_connection")
    @patch("app.core.metrics.generate_latest")
    def test_returns_prometheus_format(self, mock_gen, mock_redis):
        mock_gen.return_value = b"# HELP metric\n"
        mock_redis.return_value.llen.return_value = 5

        response = metrics_response()
        assert isinstance(response, Response)

    @patch("app.core.metrics.get_redis_connection")
    @patch("app.core.metrics.generate_latest")
    def test_handles_redis_failure(self, mock_gen, mock_redis):
        mock_gen.return_value = b"# HELP metric\n"
        mock_redis.side_effect = Exception("redis down")

        response = metrics_response()
        assert isinstance(response, Response)
