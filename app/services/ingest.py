"""Document ingestion pipeline.

Handles text extraction (PDF, plain text), chunking with overlap,
filename sanitization, and vector upsert into Qdrant.
"""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import List, Tuple

from pypdf import PdfReader

from app.core.config import settings
from app.services.retrieval import upsert_chunks

FILENAME_SANITIZE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def extract_text_from_bytes(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore")


def chunk_text(text: str) -> List[str]:
    normalized_text = " ".join(text.split())
    if not normalized_text:
        return []

    chunks: List[str] = []
    step = max(settings.chunk_size - settings.chunk_overlap, 1)
    for start in range(0, len(normalized_text), step):
        end = start + settings.chunk_size
        chunk = normalized_text[start:end]
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized_text):
            break
    return chunks


def normalize_ingest_filename(filename: str) -> str:
    if not filename:
        raise ValueError("Filename is required")

    # Keep only the basename to prevent directory traversal payloads.
    basename = Path(filename).name.strip()
    if not basename or "." not in basename:
        raise ValueError("Filename must include an extension")

    name_part, extension = basename.rsplit(".", 1)
    extension = extension.lower()
    if extension not in settings.ingest_allowed_extensions:
        allowed = ", ".join(settings.ingest_allowed_extensions)
        raise ValueError(f"Unsupported file type. Allowed extensions: {allowed}")

    normalized_name = FILENAME_SANITIZE_PATTERN.sub("_", name_part).strip("._-")
    if not normalized_name:
        normalized_name = "document"

    return f"{normalized_name}.{extension}"


def validate_ingest_filename(filename: str) -> str:
    normalized = normalize_ingest_filename(filename)
    return normalized.rsplit(".", 1)[-1]


def ingest_document(file_bytes: bytes, filename: str, tenant_id: str) -> Tuple[str, int]:
    extension = validate_ingest_filename(filename)
    if extension == "pdf":
        text = extract_text_from_pdf(file_bytes)
    else:
        text = extract_text_from_bytes(file_bytes)

    chunks = chunk_text(text)
    if not chunks:
        return "", 0

    document_id = upsert_chunks(chunks, source=filename, tenant_id=tenant_id)
    return document_id, len(chunks)


def ingest_document_from_path(file_path: str, filename: str, tenant_id: str) -> Tuple[str, int]:
    bytes_data = Path(file_path).read_bytes()
    return ingest_document(bytes_data, filename, tenant_id)
