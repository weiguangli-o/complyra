"""Tests for the audit API route helper functions and endpoints."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.routes.audit import _safe_csv_value, _to_record, export_audit, list_audit_logs, search_audit


def _mock_audit_row(**overrides):
    row = MagicMock()
    row.id = overrides.get("id", 1)
    row.timestamp = overrides.get("timestamp", datetime(2024, 1, 1))
    row.tenant_id = overrides.get("tenant_id", "t1")
    row.user = overrides.get("user", "alice")
    row.action = overrides.get("action", "chat_completed")
    row.input_text = overrides.get("input_text", "question")
    row.output_text = overrides.get("output_text", "answer")
    row.meta_json = overrides.get("meta_json", "{}")
    return row


class TestSafeCsvValue:
    def test_normal_value(self):
        assert _safe_csv_value("hello") == "hello"

    def test_equals_prefix(self):
        assert _safe_csv_value("=cmd") == "'=cmd"

    def test_plus_prefix(self):
        assert _safe_csv_value("+1234") == "'+1234"

    def test_minus_prefix(self):
        assert _safe_csv_value("-1234") == "'-1234"

    def test_at_prefix(self):
        assert _safe_csv_value("@import") == "'@import"

    def test_empty_string(self):
        assert _safe_csv_value("") == ""


class TestToRecord:
    def test_converts_row(self):
        row = _mock_audit_row()
        record = _to_record(row)
        assert record.id == 1
        assert record.user == "alice"
        assert record.metadata == "{}"


class TestListAuditLogs:
    @patch("app.api.routes.audit.get_logs")
    def test_returns_records(self, mock_get_logs):
        mock_get_logs.return_value = [_mock_audit_row(), _mock_audit_row(id=2)]
        result = list_audit_logs(limit=100, tenant_ids=["t1"], _current_user={"role": "admin"})
        assert len(result) == 2
        mock_get_logs.assert_called_once_with(tenant_ids=["t1"], limit=100)


class TestSearchAudit:
    @patch("app.api.routes.audit.search_audit_logs")
    def test_search_with_all_filters(self, mock_search):
        mock_search.return_value = [_mock_audit_row()]
        result = search_audit(
            username="alice",
            action="chat_completed",
            start_time="2024-01-01T00:00:00",
            end_time="2024-12-31T23:59:59",
            limit=100,
            tenant_ids=["t1"],
            _current_user={"role": "admin"},
        )
        assert len(result) == 1
        mock_search.assert_called_once()

    @patch("app.api.routes.audit.search_audit_logs")
    def test_search_without_filters(self, mock_search):
        mock_search.return_value = []
        result = search_audit(
            username=None, action=None, start_time=None, end_time=None,
            limit=100, tenant_ids=["t1"], _current_user={"role": "admin"},
        )
        assert result == []

    def test_invalid_timestamp_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            search_audit(
                username=None, action=None, start_time="not-a-date", end_time=None,
                limit=100, tenant_ids=["t1"], _current_user={"role": "admin"},
            )
        assert exc_info.value.status_code == 400


class TestExportAudit:
    @patch("app.api.routes.audit.search_audit_logs")
    def test_returns_csv_response(self, mock_search):
        mock_search.return_value = [_mock_audit_row()]
        response = export_audit(
            username=None, action=None, start_time=None, end_time=None,
            limit=1000, tenant_ids=["t1"], _current_user={"role": "admin"},
        )
        assert response.media_type == "text/csv"
        body = response.body.decode()
        assert "id,timestamp,tenant_id" in body
        assert "alice" in body

    @patch("app.api.routes.audit.search_audit_logs")
    def test_export_with_timestamps(self, mock_search):
        mock_search.return_value = []
        response = export_audit(
            username=None, action=None,
            start_time="2024-01-01T00:00:00", end_time="2024-12-31T23:59:59",
            limit=1000, tenant_ids=["t1"], _current_user={"role": "admin"},
        )
        assert response.media_type == "text/csv"

    def test_export_invalid_timestamp_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            export_audit(
                username=None, action=None, start_time="bad", end_time=None,
                limit=1000, tenant_ids=["t1"], _current_user={"role": "admin"},
            )
        assert exc_info.value.status_code == 400
