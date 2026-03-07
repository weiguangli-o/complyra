"""Tests for the LangGraph workflow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.workflow import (
    WorkflowState,
    approval_node,
    draft_node,
    final_node,
    retrieve_node,
    route_after_draft,
    run_workflow,
)


class TestRetrieveNode:
    @patch("app.services.workflow.search_chunks")
    def test_returns_matches(self, mock_search):
        mock_search.return_value = [("chunk1", 0.9, "doc.pdf")]
        state: WorkflowState = {"question": "q", "tenant_id": "t1", "user_id": "u1"}
        result = retrieve_node(state)
        assert len(result["retrieved"]) == 1
        assert result["retrieved"][0][0] == "chunk1"


class TestDraftNode:
    @patch("app.services.workflow.evaluate_output_policy")
    @patch("app.services.workflow.generate_answer")
    def test_returns_draft_with_policy(self, mock_gen, mock_policy):
        mock_gen.return_value = "raw answer"
        mock_result = MagicMock()
        mock_result.answer = "raw answer"
        mock_result.blocked = False
        mock_result.matched_rules = []
        mock_policy.return_value = mock_result

        state: WorkflowState = {
            "question": "q",
            "retrieved": [("ctx", 0.9, "src")],
        }
        result = draft_node(state)
        assert result["draft_answer"] == "raw answer"
        assert result["policy_blocked"] is False

    @patch("app.services.workflow.evaluate_output_policy")
    @patch("app.services.workflow.generate_answer")
    def test_policy_blocked(self, mock_gen, mock_policy):
        mock_gen.return_value = "secret: AKIAXXXXXXXXXXXXXXXX"
        mock_result = MagicMock()
        mock_result.answer = "blocked message"
        mock_result.blocked = True
        mock_result.matched_rules = ["AKIA pattern"]
        mock_policy.return_value = mock_result

        state: WorkflowState = {"question": "q", "retrieved": []}
        result = draft_node(state)
        assert result["policy_blocked"] is True
        assert len(result["policy_violations"]) == 1


class TestApprovalNode:
    @patch("app.services.workflow.create_approval_request")
    def test_creates_approval(self, mock_create):
        mock_create.return_value = "approval-123"
        state: WorkflowState = {
            "user_id": "u1",
            "tenant_id": "t1",
            "question": "q",
            "draft_answer": "answer",
        }
        result = approval_node(state)
        assert result["approval_required"] is True
        assert result["approval_id"] == "approval-123"


class TestFinalNode:
    def test_marks_no_approval(self):
        result = final_node({})
        assert result["approval_required"] is False


class TestRouteAfterDraft:
    def test_policy_blocked_goes_final(self):
        assert route_after_draft({"policy_blocked": True}) == "final"

    @patch("app.services.workflow.settings")
    def test_approval_required(self, mock_settings):
        mock_settings.require_approval = True
        assert route_after_draft({"policy_blocked": False}) == "approval"

    @patch("app.services.workflow.settings")
    def test_no_approval_goes_final(self, mock_settings):
        mock_settings.require_approval = False
        assert route_after_draft({"policy_blocked": False}) == "final"


class TestRunWorkflow:
    @patch("app.services.workflow.workflow_graph")
    def test_invokes_graph(self, mock_graph):
        mock_graph.invoke.return_value = {"draft_answer": "ok"}
        result = run_workflow("q", "t1", "u1")
        assert result["draft_answer"] == "ok"
        mock_graph.invoke.assert_called_once_with(
            {"question": "q", "tenant_id": "t1", "user_id": "u1"}
        )
