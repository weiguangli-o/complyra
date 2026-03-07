"""Audit logging service.

Records all user actions (chat, ingest, approval decisions) for
compliance and traceability.
"""

from __future__ import annotations

from datetime import datetime

from app.db.audit_db import insert_log, list_logs, search_logs


def log_event(
    *,
    tenant_id: str,
    user: str,
    action: str,
    input_text: str,
    output_text: str,
    metadata: str,
) -> None:
    insert_log(
        tenant_id=tenant_id,
        user=user,
        action=action,
        input_text=input_text,
        output_text=output_text,
        metadata=metadata,
    )


def get_logs(*, tenant_ids: list[str], limit: int = 100):
    return list_logs(tenant_ids=tenant_ids, limit=limit)


def search_audit_logs(
    *,
    tenant_ids: list[str],
    username: str | None,
    action: str | None,
    start_time: datetime | None,
    end_time: datetime | None,
    limit: int,
):
    return search_logs(
        tenant_ids=tenant_ids,
        username=username,
        action=action,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
