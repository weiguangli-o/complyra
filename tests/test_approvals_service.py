"""Tests for the approvals service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.approvals import (
    create_approval_request,
    decide_approval,
    get_approval_request,
    list_approval_requests,
)


class TestCreateApprovalRequest:
    @patch("app.services.approvals.create_approval")
    def test_creates_and_returns_id(self, mock_create):
        result = create_approval_request(
            user_id="u1",
            tenant_id="t1",
            question="q",
            draft_answer="a",
        )
        assert isinstance(result, str)
        assert len(result) > 0
        mock_create.assert_called_once()


class TestListApprovalRequests:
    @patch("app.services.approvals.list_approvals")
    def test_delegates(self, mock_list):
        mock_list.return_value = []
        result = list_approval_requests(tenant_ids=["t1"], status="pending", limit=50)
        assert result == []


class TestGetApprovalRequest:
    @patch("app.services.approvals.get_approval")
    def test_returns_approval(self, mock_get):
        mock_get.return_value = MagicMock(approval_id="a1")
        result = get_approval_request("a1")
        assert result.approval_id == "a1"


class TestDecideApproval:
    @patch("app.services.approvals.update_approval")
    @patch("app.services.approvals.get_approval")
    def test_approve(self, mock_get, mock_update):
        current = MagicMock()
        current.draft_answer = "the answer"
        mock_get.return_value = current
        mock_update.return_value = MagicMock()

        decide_approval(
            approval_id="a1", approved=True, decision_by="admin", note="ok"
        )
        mock_update.assert_called_once_with(
            approval_id="a1",
            status="approved",
            decision_by="admin",
            decision_note="ok",
            final_answer="the answer",
        )

    @patch("app.services.approvals.update_approval")
    @patch("app.services.approvals.get_approval")
    def test_reject(self, mock_get, mock_update):
        mock_get.return_value = MagicMock()
        decide_approval(
            approval_id="a1", approved=False, decision_by="admin", note="no"
        )
        mock_update.assert_called_once_with(
            approval_id="a1",
            status="rejected",
            decision_by="admin",
            decision_note="no",
            final_answer=None,
        )
