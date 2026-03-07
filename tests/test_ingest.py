"""Tests for the document ingestion pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.ingest import (
    chunk_text,
    extract_text_from_bytes,
    extract_text_from_pdf,
    ingest_document,
    ingest_document_from_path,
    normalize_ingest_filename,
    validate_ingest_filename,
)


class TestExtractTextFromBytes:
    def test_decodes_utf8(self):
        text = extract_text_from_bytes(b"hello world")
        assert text == "hello world"

    def test_handles_invalid_encoding(self):
        text = extract_text_from_bytes(b"\xff\xfe")
        assert isinstance(text, str)


class TestExtractTextFromPdf:
    @patch("app.services.ingest.PdfReader")
    def test_extracts_pages(self, MockReader):
        page1 = MagicMock()
        page1.extract_text.return_value = "Page 1 content"
        page2 = MagicMock()
        page2.extract_text.return_value = "Page 2 content"
        mock_reader = MagicMock()
        mock_reader.pages = [page1, page2]
        MockReader.return_value = mock_reader

        result = extract_text_from_pdf(b"fake-pdf-bytes")
        assert "Page 1 content" in result
        assert "Page 2 content" in result

    @patch("app.services.ingest.PdfReader")
    def test_handles_none_page_text(self, MockReader):
        page = MagicMock()
        page.extract_text.return_value = None
        mock_reader = MagicMock()
        mock_reader.pages = [page]
        MockReader.return_value = mock_reader

        result = extract_text_from_pdf(b"fake-pdf")
        assert result == ""


class TestChunkText:
    def test_chunks_long_text(self):
        text = "a " * 1000
        chunks = chunk_text(text)
        assert len(chunks) > 1

    def test_empty_text(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_short_text_single_chunk(self):
        chunks = chunk_text("short text here")
        assert len(chunks) == 1
        assert chunks[0] == "short text here"

    def test_whitespace_normalized(self):
        chunks = chunk_text("hello   world\n\nfoo")
        assert chunks[0] == "hello world foo"


class TestNormalizeIngestFilename:
    def test_valid_filename(self):
        assert normalize_ingest_filename("report.pdf") == "report.pdf"

    def test_strips_directory_traversal(self):
        result = normalize_ingest_filename("../../etc/passwd.txt")
        assert "/" not in result
        assert result.endswith(".txt")

    def test_sanitizes_special_chars(self):
        result = normalize_ingest_filename("my file (1).pdf")
        assert " " not in result
        assert "(" not in result

    def test_empty_filename_raises(self):
        with pytest.raises(ValueError, match="Filename is required"):
            normalize_ingest_filename("")

    def test_no_extension_raises(self):
        with pytest.raises(ValueError, match="extension"):
            normalize_ingest_filename("noextension")

    def test_unsupported_extension_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            normalize_ingest_filename("file.exe")

    def test_fallback_name_for_special_chars_only(self):
        result = normalize_ingest_filename("!!!.pdf")
        assert result == "document.pdf"


class TestValidateIngestFilename:
    def test_returns_extension(self):
        assert validate_ingest_filename("doc.pdf") == "pdf"

    def test_returns_txt(self):
        assert validate_ingest_filename("notes.txt") == "txt"

    def test_returns_md(self):
        assert validate_ingest_filename("readme.md") == "md"


class TestIngestDocument:
    @patch("app.services.ingest.upsert_chunks")
    def test_ingests_txt(self, mock_upsert):
        mock_upsert.return_value = "doc-123"
        doc_id, count = ingest_document(b"some content here", "file.txt", "tenant1")
        assert doc_id == "doc-123"
        assert count > 0

    @patch("app.services.ingest.upsert_chunks")
    @patch("app.services.ingest.extract_text_from_pdf")
    def test_ingests_pdf(self, mock_pdf, mock_upsert):
        mock_pdf.return_value = "extracted pdf text"
        mock_upsert.return_value = "doc-456"
        doc_id, count = ingest_document(b"pdf-bytes", "report.pdf", "tenant1")
        assert doc_id == "doc-456"
        mock_pdf.assert_called_once()

    @patch("app.services.ingest.upsert_chunks")
    def test_empty_content_returns_no_chunks(self, mock_upsert):
        doc_id, count = ingest_document(b"", "empty.txt", "tenant1")
        assert doc_id == ""
        assert count == 0
        mock_upsert.assert_not_called()


class TestIngestDocumentFromPath:
    @patch("app.services.ingest.ingest_document")
    def test_reads_file_and_delegates(self, mock_ingest, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("file content")
        mock_ingest.return_value = ("doc-789", 1)

        doc_id, count = ingest_document_from_path(str(test_file), "test.txt", "t1")
        assert doc_id == "doc-789"
        mock_ingest.assert_called_once()
