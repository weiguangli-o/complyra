"""Tests for user API routes."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.routes.users import _to_user_response, assign_tenant, create_user, list_users
from app.models.schemas import AssignTenantRequest, UserCreateRequest


class TestToUserResponse:
    @patch("app.api.routes.users.list_user_tenant_access")
    def test_converts_row(self, mock_tenants):
        mock_tenants.return_value = ["t1", "t2"]
        row = MagicMock()
        row.user_id = "u1"
        row.username = "alice"
        row.role = "admin"
        row.default_tenant_id = "t1"
        row.created_at = datetime(2024, 1, 1)

        result = _to_user_response(row)
        assert result.username == "alice"
        assert result.tenant_ids == ["t1", "t2"]


class TestCreateUser:
    @patch("app.api.routes.users.log_event")
    @patch("app.api.routes.users.list_user_tenant_access")
    @patch("app.api.routes.users.list_user_accounts")
    @patch("app.api.routes.users.create_user_account")
    def test_creates_user(self, mock_create, mock_list, mock_tenants, mock_log):
        mock_create.return_value = "u1"
        row = MagicMock()
        row.user_id = "u1"
        row.username = "bob"
        row.role = "user"
        row.default_tenant_id = "t1"
        row.created_at = datetime(2024, 1, 1)
        mock_list.return_value = [row]
        mock_tenants.return_value = ["t1"]

        user = {"username": "admin", "default_tenant_id": "default"}
        result = create_user(
            UserCreateRequest(username="bob", password="pass", default_tenant_id="t1"),
            user=user,
        )
        assert result.username == "bob"

    @patch("app.api.routes.users.create_user_account")
    def test_create_failure(self, mock_create):
        mock_create.side_effect = Exception("dup")
        user = {"username": "admin", "default_tenant_id": "default"}
        with pytest.raises(HTTPException) as exc_info:
            create_user(
                UserCreateRequest(username="bob", password="pass"), user=user
            )
        assert exc_info.value.status_code == 400

    @patch("app.api.routes.users.list_user_accounts")
    @patch("app.api.routes.users.create_user_account")
    def test_user_not_found_after_create(self, mock_create, mock_list):
        mock_create.return_value = "u1"
        mock_list.return_value = []
        user = {"username": "admin", "default_tenant_id": "default"}
        with pytest.raises(HTTPException) as exc_info:
            create_user(
                UserCreateRequest(username="bob", password="pass"), user=user
            )
        assert exc_info.value.status_code == 500


class TestListUsers:
    @patch("app.api.routes.users.list_user_tenant_access")
    @patch("app.api.routes.users.list_user_accounts")
    def test_returns_list(self, mock_list, mock_tenants):
        row = MagicMock()
        row.user_id = "u1"
        row.username = "alice"
        row.role = "admin"
        row.default_tenant_id = "t1"
        row.created_at = datetime(2024, 1, 1)
        mock_list.return_value = [row]
        mock_tenants.return_value = ["t1"]

        result = list_users(_current_user={"role": "admin"})
        assert len(result) == 1


class TestAssignTenant:
    @patch("app.api.routes.users.log_event")
    @patch("app.api.routes.users.assign_user_to_tenant")
    def test_assign_success(self, mock_assign, mock_log):
        user = {"username": "admin", "default_tenant_id": "default"}
        result = assign_tenant(
            "u1", AssignTenantRequest(tenant_id="t2"), user=user
        )
        assert result["status"] == "ok"

    @patch("app.api.routes.users.assign_user_to_tenant")
    def test_assign_failure(self, mock_assign):
        mock_assign.side_effect = Exception("fail")
        user = {"username": "admin", "default_tenant_id": "default"}
        with pytest.raises(HTTPException) as exc_info:
            assign_tenant("u1", AssignTenantRequest(tenant_id="t2"), user=user)
        assert exc_info.value.status_code == 400
