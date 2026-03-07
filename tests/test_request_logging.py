"""Tests for RequestLoggingMiddleware."""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from app.core.request_logging import RequestLoggingMiddleware


def _make_app(raise_error=False):
    app = Starlette()

    @app.route("/ok")
    async def ok(request: Request):
        return PlainTextResponse("ok")

    @app.route("/error")
    async def error(request: Request):
        raise RuntimeError("boom")

    app.add_middleware(RequestLoggingMiddleware)
    return app


def test_logs_successful_request():
    app = _make_app()
    client = TestClient(app)
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.text == "ok"


def test_logs_failed_request():
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/error")
    assert resp.status_code == 500
