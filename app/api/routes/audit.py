"""Audit log viewing and CSV export for compliance.

Audit logs record every significant action in the system — who did what,
when, and for which tenant. They are critical for compliance because
regulations (SOC 2, ISO 27001, etc.) require organizations to maintain
an immutable record of all access and changes to sensitive data.

This module provides endpoints to:
  - List recent audit log entries
  - Search/filter audit logs by user, action, and time range
  - Export audit logs as a CSV file for offline review or compliance audits
"""

from __future__ import annotations

import csv
import io

from dateutil import parser
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.api.deps import get_accessible_tenant_ids, require_roles
from app.models.schemas import AuditRecord
from app.services.audit import get_logs, search_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])


def _to_record(row) -> AuditRecord:
    """Convert a database audit row into an API response object."""
    return AuditRecord(
        id=row.id,
        timestamp=row.timestamp,
        tenant_id=row.tenant_id,
        user=row.user,
        action=row.action,
        input_text=row.input_text,
        output_text=row.output_text,
        metadata=row.meta_json,
    )


def _safe_csv_value(value: str) -> str:
    """Sanitize a string value before writing it into a CSV cell.

    CSV injection prevention: If a cell value starts with =, +, -, or @,
    spreadsheet programs like Excel or Google Sheets will interpret it as
    a formula. An attacker could craft audit log data (e.g., a username)
    like "=CMD('malicious command')" which would execute when someone
    opens the exported CSV in a spreadsheet. By prepending a single quote,
    we force the spreadsheet to treat the cell as plain text.
    """
    if value and value[0] in {"=", "+", "-", "@"}:
        return f"'{value}"
    return value


@router.get("/", response_model=list[AuditRecord])
def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    tenant_ids: list[str] = Depends(get_accessible_tenant_ids),
    _current_user: dict = Depends(require_roles(["admin", "auditor"])),
):
    """List the most recent audit log entries.

    Returns audit records for all tenants the current user can access,
    ordered by most recent first. Only admins and auditors can view logs.
    """
    rows = get_logs(tenant_ids=tenant_ids, limit=limit)
    return [_to_record(row) for row in rows]


@router.get("/search", response_model=list[AuditRecord])
def search_audit(
    username: str | None = Query(default=None, alias="user"),
    action: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    limit: int = Query(100, ge=1, le=1000),
    tenant_ids: list[str] = Depends(get_accessible_tenant_ids),
    _current_user: dict = Depends(require_roles(["admin", "auditor"])),
):
    """Search audit logs with filters for user, action, and time range.

    This is the advanced search endpoint. You can filter by:
      - user: who performed the action
      - action: what type of action (e.g., "login", "ingest_submitted")
      - start_time / end_time: ISO 8601 timestamps to limit the date range
    """
    try:
        start_dt = parser.isoparse(start_time) if start_time else None
        end_dt = parser.isoparse(end_time) if end_time else None
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid timestamp format") from exc

    rows = search_audit_logs(
        tenant_ids=tenant_ids,
        username=username,
        action=action,
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
    )
    return [_to_record(row) for row in rows]


@router.get("/export")
def export_audit(
    username: str | None = Query(default=None, alias="user"),
    action: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    limit: int = Query(1000, ge=1, le=5000),
    tenant_ids: list[str] = Depends(get_accessible_tenant_ids),
    _current_user: dict = Depends(require_roles(["admin", "auditor"])),
):
    """Export audit logs as a downloadable CSV file.

    This is used during compliance audits when an auditor needs to review
    logs offline or attach them to a compliance report. The CSV file
    includes all the same fields as the JSON endpoints. Cell values are
    sanitized to prevent CSV injection attacks (see _safe_csv_value).
    """
    try:
        start_dt = parser.isoparse(start_time) if start_time else None
        end_dt = parser.isoparse(end_time) if end_time else None
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid timestamp format") from exc

    rows = search_audit_logs(
        tenant_ids=tenant_ids,
        username=username,
        action=action,
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "timestamp", "tenant_id", "user", "action", "input_text", "output_text", "metadata"]
    )
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.timestamp.isoformat(),
                row.tenant_id,
                _safe_csv_value(row.user),
                _safe_csv_value(row.action),
                _safe_csv_value(row.input_text),
                _safe_csv_value(row.output_text),
                _safe_csv_value(row.meta_json),
            ]
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_export.csv"},
    )
