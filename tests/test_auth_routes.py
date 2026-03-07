"""Tests for the auth routes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.routes.auth import login, logout
from app.models.schemas import LoginRequest


class TestLogin:
    @patch("app.api.routes.auth.create_access_token")
    @patch("app.api.routes.auth.authenticate_user")
    def test_successful_login(self, mock_auth, mock_token):
        mock_auth.return_value = {
            "username": "alice",
            "role": "admin",
            "user_id": "u1",
            "default_tenant_id": "t1",
        }
        mock_token.return_value = "jwt-token"
        response = MagicMock()

        result = login(LoginRequest(username="alice", password="pass"), response)
        assert result.access_token == "jwt-token"
        assert result.role == "admin"
        response.set_cookie.assert_called_once()

    @patch("app.api.routes.auth.authenticate_user")
    def test_invalid_credentials(self, mock_auth):
        mock_auth.return_value = None
        response = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            login(LoginRequest(username="bad", password="wrong"), response)
        assert exc_info.value.status_code == 401


class TestLogout:
    def test_clears_cookie(self):
        response = MagicMock()
        result = logout(response)
        assert result["status"] == "ok"
        response.delete_cookie.assert_called_once()
