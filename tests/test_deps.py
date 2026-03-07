"""Tests for API dependency injection."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.deps import (
    _extract_token,
    get_accessible_tenant_ids,
    get_current_user,
    get_tenant_id,
    require_roles,
)


class TestExtractToken:
    def test_bearer_token(self):
        token = _extract_token("Bearer abc123", None)
        assert token == "abc123"

    def test_cookie_token(self):
        token = _extract_token(None, "cookie-token")
        assert token == "cookie-token"

    def test_bearer_takes_priority(self):
        token = _extract_token("Bearer header-token", "cookie-token")
        assert token == "header-token"

    def test_missing_both_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            _extract_token(None, None)
        assert exc_info.value.status_code == 401


class TestGetCurrentUser:
    @patch("app.api.deps.get_user_profile")
    @patch("app.api.deps.jwt")
    def test_valid_token(self, mock_jwt, mock_profile):
        mock_jwt.decode.return_value = {
            "sub": "alice",
            "role": "admin",
            "uid": "u1",
            "tid": "t1",
        }
        mock_profile.return_value = {
            "user_id": "u1",
            "username": "alice",
            "role": "admin",
            "default_tenant_id": "t1",
            "tenant_ids": ["t1"],
        }
        user = get_current_user("Bearer valid-token", None)
        assert user["username"] == "alice"
        assert user["role"] == "admin"

    @patch("app.api.deps.jwt")
    def test_invalid_token_raises(self, mock_jwt):
        from jose import JWTError
        mock_jwt.decode.side_effect = JWTError("bad token")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user("Bearer bad-token", None)
        assert exc_info.value.status_code == 401

    @patch("app.api.deps.get_user_profile")
    @patch("app.api.deps.jwt")
    def test_missing_claims_raises(self, mock_jwt, mock_profile):
        mock_jwt.decode.return_value = {"sub": None, "role": None, "uid": None}
        with pytest.raises(HTTPException) as exc_info:
            get_current_user("Bearer token", None)
        assert exc_info.value.status_code == 401

    @patch("app.api.deps.get_user_profile")
    @patch("app.api.deps.jwt")
    def test_deleted_user_raises(self, mock_jwt, mock_profile):
        mock_jwt.decode.return_value = {
            "sub": "alice", "role": "user", "uid": "u1", "tid": "t1"
        }
        mock_profile.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            get_current_user("Bearer token", None)
        assert exc_info.value.status_code == 401


class TestRequireRoles:
    def test_allowed_role(self):
        guard = require_roles(["admin", "auditor"])
        user = {"role": "admin", "username": "a", "user_id": "1", "tenant_ids": []}
        result = guard(user=user)
        assert result["role"] == "admin"

    def test_forbidden_role(self):
        guard = require_roles(["admin"])
        user = {"role": "user", "username": "a", "user_id": "1", "tenant_ids": []}
        with pytest.raises(HTTPException) as exc_info:
            guard(user=user)
        assert exc_info.value.status_code == 403


class TestGetTenantId:
    @patch("app.api.deps.user_has_tenant_access")
    def test_uses_header(self, mock_access):
        mock_access.return_value = True
        user = {"user_id": "u1", "default_tenant_id": "t1", "tenant_ids": ["t1", "t2"]}
        tid = get_tenant_id(user=user, x_tenant_id="t2")
        assert tid == "t2"

    @patch("app.api.deps.user_has_tenant_access")
    def test_falls_back_to_default(self, mock_access):
        mock_access.return_value = True
        user = {"user_id": "u1", "default_tenant_id": "t1", "tenant_ids": ["t1"]}
        tid = get_tenant_id(user=user, x_tenant_id=None)
        assert tid == "t1"

    @patch("app.api.deps.user_has_tenant_access")
    def test_denied_tenant_raises(self, mock_access):
        mock_access.return_value = False
        user = {"user_id": "u1", "default_tenant_id": "t1", "tenant_ids": ["t1"]}
        with pytest.raises(HTTPException) as exc_info:
            get_tenant_id(user=user, x_tenant_id="t999")
        assert exc_info.value.status_code == 403


class TestGetAccessibleTenantIds:
    def test_returns_tenant_ids(self):
        user = {"tenant_ids": ["t1", "t2"]}
        assert get_accessible_tenant_ids(user=user) == ["t1", "t2"]
