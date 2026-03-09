"""Document ingestion pipeline.

Handles text extraction (PDF, plain text, images), chunking with overlap,
filename sanitization, and vector upsert into Qdrant.
Supports OCR fallback via pytesseract for scanned PDF pages and
multimodal image description via Gemini Vision.

How it works at a high level:
1. A file (PDF, text, or image) comes in as raw bytes.
2. We extract readable text from the file. For PDFs, we try the built-in
   text layer first; if that yields very little text (likely a scanned
   document), we fall back to OCR (optical character recognition).
3. The extracted text is split into smaller pieces called "chunks" so that
   each chunk fits within the embedding model's context window and
   produces a focused vector representation.
4. Each chunk is converted into a numeric vector (embedding) and stored
   in the Qdrant vector database for later similarity search.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from app.core.config import settings
from app.services.retrieval import upsert_chunks

logger = logging.getLogger(__name__)

# This pattern matches any character that is NOT a letter, digit, dot, underscore,
# or hyphen. We use it later to replace "unsafe" characters in filenames with
# underscores, preventing directory-traversal attacks and filesystem issues.
FILENAME_SANITIZE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass
class PageContent:
    """Text content extracted from a single PDF page."""

    text: str
    page_number: int


@dataclass
class ChunkWithMetadata:
    """A text chunk with metadata about its source pages."""

    text: str
    page_numbers: List[int] = field(default_factory=list)
    chunk_index: int = 0


def _ocr_page(page) -> str:
    """Run OCR on a single PDF page using pytesseract.

    OCR (Optical Character Recognition) converts an image of text into
    actual text characters. We render the PDF page as a 300-DPI image
    (high enough resolution for accurate recognition) and pass it to
    the Tesseract OCR engine.
    """
    import pytesseract
    from PIL import Image

    # Render the PDF page to a pixel-map (bitmap image) at 300 DPI.
    # Higher DPI means more detail, which improves OCR accuracy.
    pix = page.get_pixmap(dpi=300)
    # Convert the raw pixel data into a PIL Image object that pytesseract can read.
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    # Run Tesseract OCR on the image and return the recognized text.
    return pytesseract.image_to_string(img, lang=settings.ocr_language)


def _enrich_with_image_descriptions(doc, page, text: str) -> str:
    """Extract images from a PDF page and append Gemini Vision descriptions.

    Only processes images wider than 100 pixels to skip tiny icons/decorations.
    """
    from app.services.llm import describe_image

    try:
        image_list = page.get_images(full=True)
    except Exception:
        return text

    for img_info in image_list:
        xref = img_info[0]
        try:
            base_image = doc.extract_image(xref)
            if not base_image or "image" not in base_image:
                continue
            width = base_image.get("width", 0)
            if width <= 100:
                continue
            image_bytes = base_image["image"]
            description = describe_image(image_bytes)
            if description:
                text += f"\n\n[Image description: {description}]"
        except Exception:
            logger.debug("Failed to extract/describe image xref=%d", xref)
            continue

    return text


def extract_text_from_pdf(file_bytes: bytes) -> List[PageContent]:
    """Extract text from a PDF, with optional OCR fallback for scanned pages.

    Returns a list of PageContent with text and 1-based page numbers.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages: List[PageContent] = []

    for page_num, page in enumerate(doc, start=1):
        # First, try to extract text from the PDF's native text layer.
        # This works for digitally-created PDFs but returns little/no text
        # for scanned documents (which are essentially images).
        text = page.get_text() or ""

        # OCR fallback logic: if the PDF page has fewer characters than
        # the configured threshold (ocr_min_text_threshold), it is probably
        # a scanned document — the page is an image, not searchable text.
        # In that case, we use OCR to "read" the image and extract text.
        if settings.ocr_enabled and len(text.strip()) < settings.ocr_min_text_threshold:
            try:
                ocr_text = _ocr_page(page)
                if ocr_text.strip():
                    text = ocr_text
            except Exception:
                pass  # OCR failed; keep whatever text we got from the native layer

        # Multimodal: extract and describe images on the page
        if settings.multimodal_enabled:
            text = _enrich_with_image_descriptions(doc, page, text)

        pages.append(PageContent(text=text, page_number=page_num))

    doc.close()
    return pages


def extract_text_from_bytes(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore")


def chunk_text(text: str) -> List[str]:
    """Fixed-size chunking (character-level with overlap).

    This is the simpler chunking strategy. It slides a fixed-size window
    across the text, advancing by (chunk_size - chunk_overlap) characters
    each step. The overlap ensures that information near a chunk boundary
    is not lost — it appears in both the current chunk and the next one,
    so the embedding model can capture context that spans the boundary.
    """
    # Collapse all whitespace (newlines, tabs, multiple spaces) into single
    # spaces so chunks are clean and consistently formatted.
    normalized_text = " ".join(text.split())
    if not normalized_text:
        return []

    chunks: List[str] = []
    # The step size determines how far we advance the window each iteration.
    # By subtracting chunk_overlap, consecutive chunks share some text.
    step = max(settings.chunk_size - settings.chunk_overlap, 1)
    for start in range(0, len(normalized_text), step):
        end = start + settings.chunk_size
        chunk = normalized_text[start:end]
        if chunk:
            chunks.append(chunk)
        # Stop once we have reached the end of the text.
        if end >= len(normalized_text):
            break
    return chunks


def smart_chunk_text(pages: List[PageContent]) -> List[ChunkWithMetadata]:
    """Split pages into chunks using paragraph and sentence boundaries.

    Unlike the simple fixed-size chunker (chunk_text), this "smart" chunker
    tries to keep semantically meaningful units together. The algorithm has
    three steps:

    Step 1 — Paragraph detection:
        Split each page's text on double newlines. Each resulting block is
        treated as a paragraph — a self-contained unit of meaning.

    Step 2 — Sentence splitting (for oversized paragraphs):
        If a paragraph is longer than the configured chunk_size, we break
        it into individual sentences so no single segment is too large
        for the embedding model.

    Step 3 — Chunk merging:
        Walk through all segments and greedily merge them into chunks. We
        keep adding segments to the current chunk as long as the total
        length stays within chunk_size. When a new segment would exceed
        the limit, we finalize the current chunk and start a new one —
        optionally carrying over the tail end of the previous chunk
        (the "overlap") so that context near the boundary is preserved.

    Each chunk records which page number(s) its content came from, which
    allows the UI to show page references alongside search results.
    """
    chunk_size = settings.chunk_size
    chunk_overlap = settings.chunk_overlap

    # ── Step 1: Paragraph detection ──────────────────────────────────────
    # Split each page's text by double newlines (blank lines between
    # paragraphs). This preserves the document's natural structure.
    paragraphs: List[Tuple[str, int]] = []
    for page in pages:
        raw_paragraphs = re.split(r"\n\s*\n", page.text)
        for para in raw_paragraphs:
            cleaned = para.strip()
            if cleaned:
                paragraphs.append((cleaned, page.page_number))

    if not paragraphs:
        return []

    # ── Step 2: Sentence splitting ───────────────────────────────────────
    # If a paragraph is too long to fit in a single chunk, break it into
    # sentences. The regex splits after sentence-ending punctuation
    # (periods, exclamation marks, question marks — including Chinese
    # equivalents) followed by whitespace.
    segments: List[Tuple[str, int]] = []
    sentence_pattern = re.compile(r"(?<=[.!?。！？])\s+")
    for para_text, page_num in paragraphs:
        if len(para_text) <= chunk_size:
            # Paragraph fits in one chunk — keep it as a single segment.
            segments.append((para_text, page_num))
        else:
            # Paragraph is too long — split it into individual sentences.
            sentences = sentence_pattern.split(para_text)
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    segments.append((sentence, page_num))

    # ── Step 3: Chunk merging ────────────────────────────────────────────
    # Greedily merge segments into chunks, respecting the maximum chunk_size.
    chunks: List[ChunkWithMetadata] = []
    current_text = ""
    current_pages: List[int] = []
    chunk_index = 0

    for seg_text, page_num in segments:
        # Try appending the next segment to the current chunk.
        candidate = (current_text + "\n\n" + seg_text).strip() if current_text else seg_text

        if len(candidate) <= chunk_size:
            # It fits — keep building the current chunk.
            current_text = candidate
            if page_num not in current_pages:
                current_pages.append(page_num)
        else:
            # It does not fit — finalize (flush) the current chunk.
            if current_text:
                chunks.append(
                    ChunkWithMetadata(
                        text=current_text,
                        page_numbers=list(current_pages),
                        chunk_index=chunk_index,
                    )
                )
                chunk_index += 1

                # Handle overlap: carry over the last `chunk_overlap` characters
                # from the just-finalized chunk into the new one. This ensures
                # that information near chunk boundaries appears in both chunks,
                # improving retrieval quality for queries that span a boundary.
                if chunk_overlap > 0 and len(current_text) > chunk_overlap:
                    overlap_text = current_text[-chunk_overlap:]
                    current_text = (overlap_text + "\n\n" + seg_text).strip()
                    current_pages = list(current_pages)  # carry over pages from overlap
                    if page_num not in current_pages:
                        current_pages.append(page_num)
                else:
                    current_text = seg_text
                    current_pages = [page_num]
            else:
                # Edge case: a single segment exceeds chunk_size. We cannot
                # split it further without breaking mid-sentence, so we
                # accept it as-is. It will be slightly oversized.
                current_text = seg_text
                current_pages = [page_num]

    # Flush any remaining text as the final chunk.
    if current_text.strip():
        chunks.append(
            ChunkWithMetadata(
                text=current_text,
                page_numbers=list(current_pages),
                chunk_index=chunk_index,
            )
        )

    return chunks


def normalize_ingest_filename(filename: str) -> str:
    """Sanitize a user-provided filename for safe storage.

    Why we do this:
    - Users might upload files with special characters, spaces, or even
      directory traversal payloads like "../../etc/passwd".
    - We strip everything except the basename, replace unsafe characters
      with underscores, and validate the extension against an allow-list.
    """
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
    """Main entry point for the ingestion pipeline.

    Takes raw file bytes, extracts text (with OCR fallback for scanned PDFs
    and Gemini Vision for images), splits the text into chunks, embeds them,
    and stores the vectors in Qdrant.

    Returns a tuple of (document_id, number_of_chunks_created).
    """
    import time

    from app.core.metrics import (
        CHUNKS_PRODUCED_TOTAL,
        DOCUMENT_INGEST_DURATION,
        DOCUMENT_INGEST_TOTAL,
    )

    ingest_start = time.perf_counter()
    extension = validate_ingest_filename(filename)

    try:
        if extension in ("png", "jpg", "jpeg"):
            from app.services.llm import describe_image

            description = describe_image(file_bytes)
            if not description:
                DOCUMENT_INGEST_TOTAL.labels(file_type=extension, status="empty").inc()
                return "", 0
            text = f"[Image: {filename}]\n\n[Image description: {description}]"
            chunks = chunk_text(text) if len(text) > settings.chunk_size else [text]
            if not chunks:
                DOCUMENT_INGEST_TOTAL.labels(file_type=extension, status="empty").inc()
                return "", 0
            document_id = upsert_chunks(chunks, source=filename, tenant_id=tenant_id)
            CHUNKS_PRODUCED_TOTAL.inc(len(chunks))
            DOCUMENT_INGEST_TOTAL.labels(file_type=extension, status="success").inc()
            DOCUMENT_INGEST_DURATION.labels(file_type=extension).observe(
                time.perf_counter() - ingest_start
            )
            return document_id, len(chunks)
        elif extension == "pdf":
            pages = extract_text_from_pdf(file_bytes)

            if settings.chunking_strategy == "smart":
                smart_chunks = smart_chunk_text(pages)
                if not smart_chunks:
                    DOCUMENT_INGEST_TOTAL.labels(file_type="pdf", status="empty").inc()
                    return "", 0
                chunk_texts = [c.text for c in smart_chunks]
                chunk_page_numbers = [c.page_numbers for c in smart_chunks]
                document_id = upsert_chunks(
                    chunk_texts,
                    source=filename,
                    tenant_id=tenant_id,
                    page_numbers=chunk_page_numbers,
                )
                CHUNKS_PRODUCED_TOTAL.inc(len(smart_chunks))
                DOCUMENT_INGEST_TOTAL.labels(file_type="pdf", status="success").inc()
                DOCUMENT_INGEST_DURATION.labels(file_type="pdf").observe(
                    time.perf_counter() - ingest_start
                )
                return document_id, len(smart_chunks)
            else:
                full_text = "\n".join(p.text for p in pages)
                chunks = chunk_text(full_text)
                if not chunks:
                    DOCUMENT_INGEST_TOTAL.labels(file_type="pdf", status="empty").inc()
                    return "", 0
                document_id = upsert_chunks(chunks, source=filename, tenant_id=tenant_id)
                CHUNKS_PRODUCED_TOTAL.inc(len(chunks))
                DOCUMENT_INGEST_TOTAL.labels(file_type="pdf", status="success").inc()
                DOCUMENT_INGEST_DURATION.labels(file_type="pdf").observe(
                    time.perf_counter() - ingest_start
                )
                return document_id, len(chunks)
        else:
            text = extract_text_from_bytes(file_bytes)
            chunks = chunk_text(text)
            if not chunks:
                DOCUMENT_INGEST_TOTAL.labels(file_type=extension, status="empty").inc()
                return "", 0
            document_id = upsert_chunks(chunks, source=filename, tenant_id=tenant_id)
            CHUNKS_PRODUCED_TOTAL.inc(len(chunks))
            DOCUMENT_INGEST_TOTAL.labels(file_type=extension, status="success").inc()
            DOCUMENT_INGEST_DURATION.labels(file_type=extension).observe(
                time.perf_counter() - ingest_start
            )
            return document_id, len(chunks)
    except Exception:
        DOCUMENT_INGEST_TOTAL.labels(file_type=extension, status="error").inc()
        raise


def ingest_document_from_path(file_path: str, filename: str, tenant_id: str) -> Tuple[str, int]:
    bytes_data = Path(file_path).read_bytes()
    return ingest_document(bytes_data, filename, tenant_id)
