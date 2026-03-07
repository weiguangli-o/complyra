"""Tests for the audit logging service."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from app.services.audit import get_logs, log_event, search_audit_logs


class TestLogEvent:
    @patch("app.services.audit.insert_log")
    def test_delegates_to_db(self, mock_insert):
        log_event(
            tenant_id="t1",
            user="alice",
            action="chat_completed",
            input_text="question",
            output_text="answer",
            metadata="{}",
        )
        mock_insert.assert_called_once_with(
            tenant_id="t1",
            user="alice",
            action="chat_completed",
            input_text="question",
            output_text="answer",
            metadata="{}",
        )


class TestGetLogs:
    @patch("app.services.audit.list_logs")
    def test_delegates_to_db(self, mock_list):
        mock_list.return_value = []
        result = get_logs(tenant_ids=["t1"], limit=50)
        assert result == []
        mock_list.assert_called_once_with(tenant_ids=["t1"], limit=50)


class TestSearchAuditLogs:
    @patch("app.services.audit.search_logs")
    def test_delegates_to_db(self, mock_search):
        mock_search.return_value = []
        now = datetime.now()
        result = search_audit_logs(
            tenant_ids=["t1"],
            username="alice",
            action="chat_completed",
            start_time=now,
            end_time=now,
            limit=100,
        )
        assert result == []
        mock_search.assert_called_once()
