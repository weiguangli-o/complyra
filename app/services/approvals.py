"""Human-in-the-loop approval workflow service.

Manages the lifecycle of approval requests: creation, listing,
retrieval, and decision recording.
"""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

from app.db.audit_db import create_approval, get_approval, list_approvals, update_approval


def create_approval_request(
    *, user_id: str, tenant_id: str, question: str, draft_answer: str
) -> str:
    """Create a new pending approval request and return its ID."""
    approval_id = str(uuid4())
    create_approval(
        approval_id=approval_id,
        user_id=user_id,
        tenant_id=tenant_id,
        question=question,
        draft_answer=draft_answer,
    )
    return approval_id


def list_approval_requests(*, tenant_ids: list[str], status: Optional[str], limit: int):
    return list_approvals(tenant_ids=tenant_ids, status=status, limit=limit)


def get_approval_request(approval_id: str):
    return get_approval(approval_id)


def decide_approval(*, approval_id: str, approved: bool, decision_by: str, note: str):
    status = "approved" if approved else "rejected"
    final_answer = None
    current = get_approval(approval_id)
    if current and approved:
        final_answer = current.draft_answer
    return update_approval(
        approval_id=approval_id,
        status=status,
        decision_by=decision_by,
        decision_note=note,
        final_answer=final_answer,
    )
