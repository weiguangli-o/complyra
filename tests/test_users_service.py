"""Tests for the users service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.users import (
    assign_user_to_tenant,
    authenticate_user,
    create_tenant_account,
    create_user_account,
    get_tenant_account,
    get_user_profile,
    list_tenant_accounts,
    list_user_accounts,
    list_user_tenant_access,
    user_has_tenant_access,
)


class TestAuthenticateUser:
    @patch("app.services.users.list_user_tenants")
    @patch("app.services.users.verify_password")
    @patch("app.services.users.get_user_by_username")
    def test_valid_credentials(self, mock_get, mock_verify, mock_tenants):
        user = MagicMock()
        user.user_id = "u1"
        user.username = "alice"
        user.role = "admin"
        user.default_tenant_id = "t1"
        user.password_hash = "hash"
        mock_get.return_value = user
        mock_verify.return_value = True
        tenant = MagicMock()
        tenant.tenant_id = "t1"
        mock_tenants.return_value = [tenant]

        result = authenticate_user("alice", "pass")
        assert result is not None
        assert result["username"] == "alice"
        assert result["tenant_ids"] == ["t1"]

    @patch("app.services.users.get_user_by_username")
    def test_user_not_found(self, mock_get):
        mock_get.return_value = None
        assert authenticate_user("nobody", "pass") is None

    @patch("app.services.users.verify_password")
    @patch("app.services.users.get_user_by_username")
    def test_wrong_password(self, mock_get, mock_verify):
        user = MagicMock()
        user.password_hash = "hash"
        mock_get.return_value = user
        mock_verify.return_value = False
        assert authenticate_user("alice", "wrong") is None


class TestGetUserProfile:
    @patch("app.services.users.list_user_tenants")
    @patch("app.services.users.get_user_by_id")
    def test_returns_profile(self, mock_get, mock_tenants):
        user = MagicMock()
        user.user_id = "u1"
        user.username = "alice"
        user.role = "admin"
        user.default_tenant_id = "t1"
        mock_get.return_value = user
        mock_tenants.return_value = []

        result = get_user_profile("u1")
        assert result["username"] == "alice"

    @patch("app.services.users.get_user_by_id")
    def test_not_found(self, mock_get):
        mock_get.return_value = None
        assert get_user_profile("u999") is None


class TestCreateUserAccount:
    @patch("app.services.users.assign_user_tenant")
    @patch("app.services.users.create_user")
    @patch("app.services.users.hash_password")
    def test_creates_user_with_tenant(self, mock_hash, mock_create, mock_assign):
        mock_hash.return_value = "hashed"
        result = create_user_account("bob", "pass", "user", "t1")
        assert isinstance(result, str)
        mock_create.assert_called_once()
        mock_assign.assert_called_once()

    @patch("app.services.users.assign_user_tenant")
    @patch("app.services.users.create_user")
    @patch("app.services.users.hash_password")
    def test_creates_user_without_tenant(self, mock_hash, mock_create, mock_assign):
        mock_hash.return_value = "hashed"
        create_user_account("bob", "pass", "user", None)
        mock_assign.assert_not_called()


class TestTenantOperations:
    @patch("app.services.users.create_tenant")
    def test_create_tenant(self, mock_create):
        create_tenant_account("t1", "Tenant One")
        mock_create.assert_called_once_with(tenant_id="t1", name="Tenant One")

    @patch("app.services.users.list_tenants")
    def test_list_tenants(self, mock_list):
        mock_list.return_value = []
        assert list_tenant_accounts() == []

    @patch("app.services.users.get_tenant")
    def test_get_tenant(self, mock_get):
        mock_get.return_value = MagicMock(tenant_id="t1")
        result = get_tenant_account("t1")
        assert result.tenant_id == "t1"

    @patch("app.services.users.list_users")
    def test_list_users(self, mock_list):
        mock_list.return_value = []
        assert list_user_accounts() == []

    @patch("app.services.users.assign_user_tenant")
    def test_assign_tenant(self, mock_assign):
        assign_user_to_tenant("u1", "t2")
        mock_assign.assert_called_once_with(user_id="u1", tenant_id="t2")

    @patch("app.services.users.list_user_tenants")
    def test_list_user_tenant_access(self, mock_list):
        t = MagicMock()
        t.tenant_id = "t1"
        mock_list.return_value = [t]
        assert list_user_tenant_access("u1") == ["t1"]

    @patch("app.services.users.user_has_tenant")
    def test_user_has_tenant_access_true(self, mock_has):
        mock_has.return_value = True
        assert user_has_tenant_access("u1", "t1") is True

    @patch("app.services.users.user_has_tenant")
    def test_user_has_tenant_access_empty_user(self, mock_has):
        assert user_has_tenant_access("", "t1") is False
