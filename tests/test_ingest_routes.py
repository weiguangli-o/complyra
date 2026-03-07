"""Tests for ingest route helper functions and endpoints."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from app.api.routes.ingest import _job_to_response, get_job, ingest_file, list_jobs


def _mock_job(**overrides):
    job = MagicMock()
    job.job_id = overrides.get("job_id", "j1")
    job.tenant_id = overrides.get("tenant_id", "t1")
    job.filename = overrides.get("filename", "doc.pdf")
    job.status = overrides.get("status", "completed")
    job.chunks_indexed = overrides.get("chunks_indexed", 10)
    job.document_id = overrides.get("document_id", "d1")
    job.error_message = overrides.get("error_message", None)
    job.created_at = overrides.get("created_at", datetime(2024, 1, 1))
    job.updated_at = overrides.get("updated_at", datetime(2024, 1, 1))
    return job


class TestJobToResponse:
    def test_converts_job(self):
        job = _mock_job()
        result = _job_to_response(job)
        assert result.job_id == "j1"
        assert result.chunks_indexed == 10
        assert result.status == "completed"


class TestGetJob:
    @patch("app.api.routes.ingest.get_ingest_job")
    def test_returns_job(self, mock_get):
        mock_get.return_value = _mock_job()
        result = get_job("j1", tenant_ids=["t1"], _current_user={"role": "admin"})
        assert result.job_id == "j1"

    @patch("app.api.routes.ingest.get_ingest_job")
    def test_not_found(self, mock_get):
        mock_get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            get_job("j1", tenant_ids=["t1"], _current_user={"role": "admin"})
        assert exc_info.value.status_code == 404

    @patch("app.api.routes.ingest.get_ingest_job")
    def test_tenant_denied(self, mock_get):
        mock_get.return_value = _mock_job(tenant_id="t2")
        with pytest.raises(HTTPException) as exc_info:
            get_job("j1", tenant_ids=["t1"], _current_user={"role": "admin"})
        assert exc_info.value.status_code == 403


class TestListJobs:
    @patch("app.api.routes.ingest.list_ingest_jobs")
    def test_returns_list(self, mock_list):
        mock_list.return_value = [_mock_job(), _mock_job(job_id="j2")]
        result = list_jobs(limit=50, tenant_ids=["t1"], _current_user={"role": "admin"})
        assert len(result) == 2


class TestIngestFile:
    @pytest.mark.asyncio
    @patch("app.api.routes.ingest.log_event")
    @patch("app.api.routes.ingest.process_ingest_job")
    @patch("app.api.routes.ingest.create_ingest_job")
    async def test_ingest_sync_success(self, mock_create_job, mock_process, mock_log, monkeypatch, tmp_path):
        monkeypatch.setattr("app.api.routes.ingest.settings.ingest_async_enabled", False)
        monkeypatch.setattr("app.api.routes.ingest.settings.ingest_max_file_size_mb", 20)
        monkeypatch.setattr("app.api.routes.ingest.settings.ingest_storage_path", str(tmp_path))

        file = UploadFile(filename="test.pdf", file=BytesIO(b"PDF content"))
        result = await ingest_file(
            file=file,
            tenant_id="t1",
            user={"user_id": "u1", "username": "admin", "role": "admin"},
        )
        assert result.status == "queued"
        mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_no_filename(self):
        file = UploadFile(filename="", file=BytesIO(b"data"))
        with pytest.raises(HTTPException) as exc_info:
            await ingest_file(
                file=file,
                tenant_id="t1",
                user={"user_id": "u1", "username": "admin", "role": "admin"},
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_ingest_file_too_large(self, monkeypatch, tmp_path):
        monkeypatch.setattr("app.api.routes.ingest.settings.ingest_max_file_size_mb", 1)
        monkeypatch.setattr("app.api.routes.ingest.settings.ingest_storage_path", str(tmp_path))

        big_data = b"x" * (1 * 1024 * 1024 + 2)
        file = UploadFile(filename="big.pdf", file=BytesIO(big_data))
        with pytest.raises(HTTPException) as exc_info:
            await ingest_file(
                file=file,
                tenant_id="t1",
                user={"user_id": "u1", "username": "admin", "role": "admin"},
            )
        assert exc_info.value.status_code == 413

    @pytest.mark.asyncio
    @patch("app.api.routes.ingest.get_ingest_queue")
    @patch("app.api.routes.ingest.create_ingest_job")
    async def test_ingest_async_enqueue_failure(self, mock_create_job, mock_queue, monkeypatch, tmp_path):
        monkeypatch.setattr("app.api.routes.ingest.settings.ingest_async_enabled", True)
        monkeypatch.setattr("app.api.routes.ingest.settings.ingest_max_file_size_mb", 20)
        monkeypatch.setattr("app.api.routes.ingest.settings.ingest_storage_path", str(tmp_path))

        mock_q = MagicMock()
        mock_q.enqueue.side_effect = Exception("redis down")
        mock_queue.return_value = mock_q

        file = UploadFile(filename="test.pdf", file=BytesIO(b"content"))
        with pytest.raises(HTTPException) as exc_info:
            await ingest_file(
                file=file,
                tenant_id="t1",
                user={"user_id": "u1", "username": "admin", "role": "admin"},
            )
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    @patch("app.api.routes.ingest.log_event")
    @patch("app.api.routes.ingest.get_ingest_queue")
    @patch("app.api.routes.ingest.create_ingest_job")
    async def test_ingest_async_success(self, mock_create_job, mock_queue, mock_log, monkeypatch, tmp_path):
        monkeypatch.setattr("app.api.routes.ingest.settings.ingest_async_enabled", True)
        monkeypatch.setattr("app.api.routes.ingest.settings.ingest_max_file_size_mb", 20)
        monkeypatch.setattr("app.api.routes.ingest.settings.ingest_storage_path", str(tmp_path))

        mock_q = MagicMock()
        mock_queue.return_value = mock_q

        file = UploadFile(filename="test.txt", file=BytesIO(b"content"))
        result = await ingest_file(
            file=file,
            tenant_id="t1",
            user={"user_id": "u1", "username": "admin", "role": "admin"},
        )
        assert result.status == "queued"
        mock_q.enqueue.assert_called_once()
