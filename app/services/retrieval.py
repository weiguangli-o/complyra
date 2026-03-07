"""Qdrant vector database integration.

Provides collection management, document upsert, and tenant-scoped
similarity search against a Qdrant instance.
"""

import logging
import uuid
from functools import lru_cache
from typing import List, Tuple

logger = logging.getLogger(__name__)

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from langsmith import traceable

from app.core.config import settings
from app.services.embeddings import embed_texts, get_embedder


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection() -> None:
    """Create the Qdrant collection if it does not exist.

    Logs a warning if the existing collection has a different vector dimension
    than the current embedding provider, which typically means the provider
    was switched and the collection needs to be recreated.
    """
    client = get_qdrant_client()
    embedder = get_embedder()
    dim = embedder.get_dimension()
    if client.collection_exists(settings.qdrant_collection):
        info = client.get_collection(settings.qdrant_collection)
        existing_dim = info.config.params.vectors.size
        if existing_dim != dim:
            logger.warning(
                "Qdrant collection '%s' has dimension %d but current embedding provider "
                "produces dimension %d. Recreate the collection to avoid errors.",
                settings.qdrant_collection,
                existing_dim,
                dim,
            )
    else:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
        )


def upsert_chunks(chunks: List[str], source: str, tenant_id: str) -> str:
    """Embed and upsert text chunks into Qdrant, returning the document ID."""
    ensure_collection()
    client = get_qdrant_client()
    vectors = embed_texts(chunks)
    document_id = str(uuid.uuid4())

    points = []
    for idx, (text, vector) in enumerate(zip(chunks, vectors)):
        points.append(
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": text,
                    "source": source,
                    "document_id": document_id,
                    "chunk_index": idx,
                    "tenant_id": tenant_id,
                },
            )
        )

    client.upsert(collection_name=settings.qdrant_collection, points=points)
    return document_id


@traceable(name="search_chunks", run_type="retriever")
def search_chunks(query: str, top_k: int, tenant_id: str) -> List[Tuple[str, float, str]]:
    ensure_collection()
    client = get_qdrant_client()
    vector = embed_texts([query])[0]
    tenant_filter = qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="tenant_id",
                match=qmodels.MatchValue(value=tenant_id),
            )
        ]
    )
    results = client.query_points(
        collection_name=settings.qdrant_collection,
        query=vector,
        limit=top_k,
        with_payload=True,
        query_filter=tenant_filter,
    )

    matches: List[Tuple[str, float, str]] = []
    for res in results.points:
        payload = res.payload or {}
        matches.append((payload.get("text", ""), res.score, payload.get("source", "")))
    return matches
