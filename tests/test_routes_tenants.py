"""Tests for tenant API routes."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.routes.tenants import create_tenant, list_tenants
from app.models.schemas import TenantCreateRequest


class TestCreateTenant:
    @patch("app.api.routes.tenants.log_event")
    @patch("app.api.routes.tenants.create_tenant_account")
    def test_creates_tenant(self, mock_create, mock_log):
        row = MagicMock()
        row.tenant_id = "test"
        row.name = "Test"
        row.created_at = datetime(2024, 1, 1)
        mock_create.return_value = row

        user = {"username": "admin", "default_tenant_id": "default"}
        result = create_tenant(TenantCreateRequest(name="Test"), user=user)
        assert result.tenant_id == "test"

    @patch("app.api.routes.tenants.log_event")
    @patch("app.api.routes.tenants.get_tenant_account")
    @patch("app.api.routes.tenants.create_tenant_account")
    def test_create_returns_none_fallback(self, mock_create, mock_get, mock_log):
        mock_create.return_value = None
        row = MagicMock()
        row.tenant_id = "test"
        row.name = "Test"
        row.created_at = datetime(2024, 1, 1)
        mock_get.return_value = row

        user = {"username": "admin", "default_tenant_id": "default"}
        result = create_tenant(TenantCreateRequest(name="Test"), user=user)
        assert result.name == "Test"

    @patch("app.api.routes.tenants.create_tenant_account")
    def test_create_failure_raises(self, mock_create):
        mock_create.side_effect = Exception("dup")
        user = {"username": "admin", "default_tenant_id": "default"}
        with pytest.raises(HTTPException) as exc_info:
            create_tenant(TenantCreateRequest(name="Test"), user=user)
        assert exc_info.value.status_code == 400

    @patch("app.api.routes.tenants.get_tenant_account")
    @patch("app.api.routes.tenants.create_tenant_account")
    def test_create_not_found_raises(self, mock_create, mock_get):
        mock_create.return_value = None
        mock_get.return_value = None
        user = {"username": "admin", "default_tenant_id": "default"}
        with pytest.raises(HTTPException) as exc_info:
            create_tenant(TenantCreateRequest(name="Test"), user=user)
        assert exc_info.value.status_code == 500


class TestListTenants:
    @patch("app.api.routes.tenants.list_tenant_accounts")
    def test_returns_list(self, mock_list):
        row = MagicMock()
        row.tenant_id = "t1"
        row.name = "One"
        row.created_at = datetime(2024, 1, 1)
        mock_list.return_value = [row]

        result = list_tenants(_current_user={"role": "admin"})
        assert len(result) == 1
        assert result[0].tenant_id == "t1"
