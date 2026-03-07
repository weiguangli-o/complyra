"""Tests for the ingest worker."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.workers.ingest_worker import process_ingest_job


class TestProcessIngestJob:
    @patch("app.workers.ingest_worker.update_ingest_job")
    @patch("app.workers.ingest_worker.ingest_document_from_path")
    def test_successful_ingestion(self, mock_ingest, mock_update, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        mock_ingest.return_value = ("doc-123", 5)

        result = process_ingest_job("j1", str(test_file), "test.txt", "t1")
        assert result["status"] == "completed"
        assert result["chunks_indexed"] == 5
        assert not test_file.exists()  # File cleaned up

    @patch("app.workers.ingest_worker.update_ingest_job")
    @patch("app.workers.ingest_worker.ingest_document_from_path")
    def test_no_text_extracted(self, mock_ingest, mock_update, tmp_path):
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")
        mock_ingest.return_value = ("", 0)

        result = process_ingest_job("j1", str(test_file), "empty.txt", "t1")
        assert result["status"] == "failed"

    @patch("app.workers.ingest_worker.update_ingest_job")
    @patch("app.workers.ingest_worker.ingest_document_from_path")
    def test_exception_handling(self, mock_ingest, mock_update, tmp_path):
        test_file = tmp_path / "bad.txt"
        test_file.write_text("data")
        mock_ingest.side_effect = Exception("parse error")

        result = process_ingest_job("j1", str(test_file), "bad.txt", "t1")
        assert result["status"] == "failed"
        assert "parse error" in result["error"]

    @patch("app.workers.ingest_worker.update_ingest_job")
    @patch("app.workers.ingest_worker.ingest_document_from_path")
    def test_file_cleanup_when_missing(self, mock_ingest, mock_update):
        mock_ingest.return_value = ("doc-1", 1)
        # Pass a non-existent path — should not raise
        result = process_ingest_job("j1", "/tmp/nonexistent_file_xyz", "f.txt", "t1")
        assert result["status"] == "completed"
