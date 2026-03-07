"""Tests for approval API routes."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.routes.approvals import (
    _to_response,
    approval_result,
    decide,
    list_approvals,
)
from app.models.schemas import ApprovalDecisionRequest


def _mock_approval(**overrides):
    row = MagicMock()
    row.approval_id = overrides.get("approval_id", "a1")
    row.user_id = overrides.get("user_id", "u1")
    row.tenant_id = overrides.get("tenant_id", "t1")
    row.status = overrides.get("status", "pending")
    row.question = overrides.get("question", "q")
    row.draft_answer = overrides.get("draft_answer", "a")
    row.final_answer = overrides.get("final_answer", None)
    row.created_at = datetime(2024, 1, 1)
    row.decided_at = overrides.get("decided_at", None)
    row.decision_by = overrides.get("decision_by", None)
    row.decision_note = overrides.get("decision_note", None)
    return row


class TestToResponse:
    def test_converts(self):
        row = _mock_approval()
        result = _to_response(row)
        assert result.approval_id == "a1"
        assert result.status == "pending"


class TestListApprovals:
    @patch("app.api.routes.approvals.list_approval_requests")
    def test_returns_list(self, mock_list):
        mock_list.return_value = [_mock_approval()]
        result = list_approvals(
            status="pending",
            tenant_id=None,
            limit=50,
            tenant_ids=["t1"],
            _current_user={"role": "admin"},
        )
        assert len(result) == 1

    @patch("app.api.routes.approvals.list_approval_requests")
    def test_filters_by_tenant(self, mock_list):
        mock_list.return_value = []
        list_approvals(
            status=None,
            tenant_id="t1",
            limit=50,
            tenant_ids=["t1", "t2"],
            _current_user={"role": "admin"},
        )
        mock_list.assert_called_once_with(tenant_ids=["t1"], status=None, limit=50)

    def test_tenant_access_denied(self):
        with pytest.raises(HTTPException) as exc_info:
            list_approvals(
                status=None,
                tenant_id="t999",
                limit=50,
                tenant_ids=["t1"],
                _current_user={"role": "admin"},
            )
        assert exc_info.value.status_code == 403


class TestDecide:
    @patch("app.api.routes.approvals.log_event")
    @patch("app.api.routes.approvals.decide_approval")
    @patch("app.api.routes.approvals.get_approval_request")
    def test_approve_success(self, mock_get, mock_decide, mock_log):
        mock_get.return_value = _mock_approval()
        mock_decide.return_value = _mock_approval(status="approved")

        result = decide(
            "a1",
            ApprovalDecisionRequest(approved=True, note="ok"),
            tenant_ids=["t1"],
            user={"username": "admin", "role": "admin"},
        )
        assert result.status == "approved"

    @patch("app.api.routes.approvals.get_approval_request")
    def test_not_found(self, mock_get):
        mock_get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            decide(
                "a1",
                ApprovalDecisionRequest(approved=True),
                tenant_ids=["t1"],
                user={"username": "admin", "role": "admin"},
            )
        assert exc_info.value.status_code == 404

    @patch("app.api.routes.approvals.get_approval_request")
    def test_tenant_denied(self, mock_get):
        mock_get.return_value = _mock_approval(tenant_id="t2")
        with pytest.raises(HTTPException) as exc_info:
            decide(
                "a1",
                ApprovalDecisionRequest(approved=True),
                tenant_ids=["t1"],
                user={"username": "admin", "role": "admin"},
            )
        assert exc_info.value.status_code == 403

    @patch("app.api.routes.approvals.get_approval_request")
    def test_already_decided(self, mock_get):
        mock_get.return_value = _mock_approval(status="approved")
        with pytest.raises(HTTPException) as exc_info:
            decide(
                "a1",
                ApprovalDecisionRequest(approved=True),
                tenant_ids=["t1"],
                user={"username": "admin", "role": "admin"},
            )
        assert exc_info.value.status_code == 400

    @patch("app.api.routes.approvals.log_event")
    @patch("app.api.routes.approvals.decide_approval")
    @patch("app.api.routes.approvals.get_approval_request")
    def test_update_failed(self, mock_get, mock_decide, mock_log):
        mock_get.return_value = _mock_approval()
        mock_decide.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            decide(
                "a1",
                ApprovalDecisionRequest(approved=True),
                tenant_ids=["t1"],
                user={"username": "admin", "role": "admin"},
            )
        assert exc_info.value.status_code == 500


class TestApprovalResult:
    @patch("app.api.routes.approvals.get_approval_request")
    def test_returns_result(self, mock_get):
        mock_get.return_value = _mock_approval(user_id="u1")
        result = approval_result(
            "a1",
            tenant_id="t1",
            user={"user_id": "u1", "role": "user"},
        )
        assert result.approval_id == "a1"

    @patch("app.api.routes.approvals.get_approval_request")
    def test_not_found(self, mock_get):
        mock_get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            approval_result("a1", tenant_id="t1", user={"user_id": "u1", "role": "user"})
        assert exc_info.value.status_code == 404

    @patch("app.api.routes.approvals.get_approval_request")
    def test_wrong_tenant(self, mock_get):
        mock_get.return_value = _mock_approval(tenant_id="t2")
        with pytest.raises(HTTPException) as exc_info:
            approval_result("a1", tenant_id="t1", user={"user_id": "u1", "role": "user"})
        assert exc_info.value.status_code == 403

    @patch("app.api.routes.approvals.get_approval_request")
    def test_wrong_user_non_admin(self, mock_get):
        mock_get.return_value = _mock_approval(user_id="u2")
        with pytest.raises(HTTPException) as exc_info:
            approval_result("a1", tenant_id="t1", user={"user_id": "u1", "role": "user"})
        assert exc_info.value.status_code == 403

    @patch("app.api.routes.approvals.get_approval_request")
    def test_admin_can_see_other_users(self, mock_get):
        mock_get.return_value = _mock_approval(user_id="u2")
        result = approval_result("a1", tenant_id="t1", user={"user_id": "u1", "role": "admin"})
        assert result.approval_id == "a1"
