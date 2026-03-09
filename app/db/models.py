"""
Database Table Definitions (ORM Models)

This file defines the database tables as Python classes using SQLAlchemy ORM
(Object-Relational Mapping). Each class below represents one table in the
database. Instead of writing raw SQL like "CREATE TABLE ...", we describe the
tables using Python classes, and SQLAlchemy translates them into actual
database tables for us.

Key concepts for non-Python readers:
  - Each class = one database table.
  - Each class attribute (like "name", "status") = one column in that table.
  - "Mapped[str]" means the column stores text; "Mapped[int]" means it stores
    a whole number; "Mapped[Optional[str]]" means the column can be empty (NULL).
  - "ForeignKey" means this column points to a row in another table, creating
    a link between the two tables.
  - "relationship" creates a convenient shortcut so you can navigate between
    linked tables in Python code (e.g., user.tenant_links).
  - "Index" makes database lookups faster for specific columns, similar to an
    index at the back of a book.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow_naive() -> datetime:
    """Return the current UTC time without timezone info.

    Many databases handle timezone-unaware ("naive") datetimes more
    consistently, so we strip the timezone after capturing UTC time.
    This is used as the default value for all timestamp columns.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Tenant(Base):
    """Represents an organization or company using the system (multi-tenancy).

    Multi-tenancy means the application serves multiple separate organizations
    from a single deployment. Each tenant's data is isolated — users in
    Tenant A cannot see Tenant B's documents or logs.

    Think of a tenant as a "workspace" or "company account".
    """

    __tablename__ = "tenants"

    # A short unique identifier for the tenant (e.g., "acme-corp").
    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    # A human-friendly display name (e.g., "Acme Corporation").
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # When this tenant was created; automatically set to the current time.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow_naive, nullable=False
    )


class User(Base):
    """Represents a person who can log in and use the system.

    Each user has login credentials (username + hashed password), a role
    that controls what they are allowed to do, and an optional default
    tenant (the workspace they see when they first log in).
    """

    __tablename__ = "users"

    # Unique ID for this user, auto-generated as a UUID if not provided.
    user_id: Mapped[str] = mapped_column(
        String(128), primary_key=True, default=lambda: str(uuid4())
    )
    # Login name; must be unique. Indexed for fast lookups during login.
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    # The password is never stored in plain text — only a secure hash.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Role controls permissions. Typical values: "admin", "reviewer", "user".
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    # The tenant this user sees by default after login. Can be empty (NULL)
    # if the user hasn't been assigned a default workspace yet.
    # This connects the User table to the Tenant table via tenant_id.
    default_tenant_id: Mapped[Optional[str]] = mapped_column(
        String(128), ForeignKey("tenants.tenant_id"), nullable=True
    )
    # When this user account was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow_naive, nullable=False
    )

    # This connects User to UserTenant — lets you access all the tenants
    # a user belongs to via user.tenant_links. "cascade=all, delete-orphan"
    # means if a user is deleted, their tenant links are automatically removed too.
    tenant_links = relationship("UserTenant", back_populates="user", cascade="all, delete-orphan")


class UserTenant(Base):
    """A many-to-many link between Users and Tenants.

    One user can belong to multiple tenants (workspaces), and one tenant
    can have multiple users. This "junction table" records which users
    belong to which tenants. Each row says: "User X has access to Tenant Y."
    """

    __tablename__ = "user_tenants"
    __table_args__ = (
        # Prevents duplicate entries — a user can only be linked to a tenant once.
        UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),
        # These indexes make it fast to look up "all tenants for a user"
        # or "all users in a tenant".
        Index("ix_user_tenants_user_id", "user_id"),
        Index("ix_user_tenants_tenant_id", "tenant_id"),
    )

    # Auto-incrementing row ID (just a simple counter: 1, 2, 3, ...).
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Which user this link is for. "ondelete=CASCADE" means if the user is
    # deleted from the users table, this link row is automatically removed.
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    # Which tenant this link is for. Also cascades on delete.
    tenant_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False
    )

    # This connects UserTenant back to User, creating a two-way link.
    # From a UserTenant row you can access the full User object via .user.
    user = relationship("User", back_populates="tenant_links")


class Approval(Base):
    """Tracks questions and answers that need human review before being shown.

    When the AI generates an answer, it may need a human (reviewer/admin)
    to approve it first. This table stores the original question, the AI's
    draft answer, the approval decision, and the final answer (which may
    be edited by the reviewer).

    Typical status flow: "pending" -> "approved" or "rejected".
    """

    __tablename__ = "approvals"
    __table_args__ = (
        # This index speeds up the common query: "show me all pending approvals
        # for tenant X" — filtering by tenant_id AND status together.
        Index("ix_approvals_tenant_status", "tenant_id", "status"),
        # This index makes it fast to find all approvals submitted by a specific user.
        Index("ix_approvals_user", "user_id"),
    )

    # Unique ID for this approval request, auto-generated as a UUID.
    approval_id: Mapped[str] = mapped_column(
        String(128), primary_key=True, default=lambda: str(uuid4())
    )
    # The user who asked the original question. Links to the users table.
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.user_id"), nullable=False)
    # Which tenant (workspace) this approval belongs to.
    tenant_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("tenants.tenant_id"), nullable=False
    )
    # The original question that was asked.
    question: Mapped[str] = mapped_column(Text, nullable=False)
    # The AI-generated answer that is waiting for review.
    draft_answer: Mapped[str] = mapped_column(Text, nullable=False)
    # The answer after review — may be the same as draft_answer, or edited.
    # NULL until a reviewer makes a decision.
    final_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Current state of this approval. Values: "pending", "approved", "rejected".
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    # When the approval request was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow_naive, nullable=False
    )
    # When a reviewer made their decision. NULL while still pending.
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    # Username or ID of the person who approved/rejected. NULL while pending.
    decision_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Optional note from the reviewer explaining why they approved or rejected.
    decision_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AuditLog(Base):
    """Records every significant action in the system for compliance tracking.

    This is an append-only log — rows are never modified or deleted.
    It captures who did what, when, and in which tenant. This is critical
    for regulatory compliance, debugging, and security investigations.

    Each row stores the user's input, the system's output, and extra
    metadata (as a JSON string) for context.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        # This index speeds up the common query: "show me recent logs for
        # tenant X, sorted by time" — filtering by tenant_id and timestamp together.
        Index("ix_audit_logs_tenant_ts", "tenant_id", "timestamp"),
        # This index makes it fast to filter logs by action type (e.g., "query", "login").
        Index("ix_audit_logs_action", "action"),
    )

    # Auto-incrementing row ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # When this action occurred.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow_naive, nullable=False
    )
    # Which tenant this action happened in.
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    # Who performed the action (username).
    user: Mapped[str] = mapped_column(String(128), nullable=False)
    # What kind of action it was (e.g., "query", "login", "document_upload").
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    # The user's input that triggered this action (e.g., the question they asked).
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    # The system's response or result of the action.
    output_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Extra details stored as a JSON string. The column is named "metadata"
    # in the actual database, but mapped to "meta_json" in Python to avoid
    # clashing with SQLAlchemy's own "metadata" attribute.
    meta_json: Mapped[str] = mapped_column("metadata", Text, nullable=False)


class IngestJob(Base):
    """Tracks the progress of uploading and processing a document.

    When a user uploads a file, the system creates an IngestJob to track
    the processing pipeline: parsing the file, splitting it into chunks,
    and indexing those chunks for search. This table lets the UI show
    progress and report errors.

    Typical status flow: "queued" -> "processing" -> "done" or "failed".
    """

    __tablename__ = "ingest_jobs"
    __table_args__ = (
        # This index speeds up: "show me recent upload jobs for tenant X".
        Index("ix_ingest_jobs_tenant_created", "tenant_id", "created_at"),
        # This index speeds up filtering by status (e.g., "show all queued jobs").
        Index("ix_ingest_jobs_status", "status"),
    )

    # Unique ID for this job.
    job_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    # Which tenant owns this job. Links to the tenants table.
    tenant_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("tenants.tenant_id"), nullable=False
    )
    # The user who uploaded the file. Links to the users table.
    created_by: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.user_id"), nullable=False
    )
    # Original name of the uploaded file.
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # Current processing state. Values: "queued", "processing", "done", "failed".
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    # How many text chunks have been indexed so far (for progress tracking).
    chunks_indexed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Once processing completes, this links to the resulting Document record.
    # NULL while the job is still in progress.
    document_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # If the job failed, this stores the error message. NULL on success.
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # When the job was created (i.e., when the file was uploaded).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow_naive, nullable=False
    )
    # When the job was last updated (e.g., status changed, chunks increased).
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow_naive, nullable=False
    )


class Document(Base):
    """Represents a document that has been fully processed and is available for search.

    After an IngestJob finishes successfully, a Document record is created.
    This stores metadata about the file (name, size, page count) and controls
    how the document behaves in the system (sensitivity level, active/archived
    status, and whether it requires approval before its content can be shown).
    """

    __tablename__ = "documents"
    __table_args__ = (
        # This index speeds up: "show me all active documents for tenant X".
        Index("ix_documents_tenant_status", "tenant_id", "status"),
        # This index speeds up: "show me all sensitive documents for tenant X".
        Index("ix_documents_tenant_sensitivity", "tenant_id", "sensitivity"),
    )

    # Unique ID for this document.
    document_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    # Which tenant owns this document. Links to the tenants table.
    tenant_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("tenants.tenant_id"), nullable=False
    )
    # Original filename (e.g., "policy_manual.pdf").
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # File format identifier (e.g., "application/pdf", "text/plain").
    mime_type: Mapped[str] = mapped_column(
        String(128), nullable=False, default="application/octet-stream"
    )
    # File size in bytes.
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Number of pages in the original document (0 for non-paginated formats).
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Number of text chunks the document was split into for search indexing.
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # How sensitive the document content is. Values: "normal", "sensitive", "restricted".
    # Higher sensitivity may trigger stricter access controls or require approval.
    sensitivity: Mapped[str] = mapped_column(String(32), nullable=False, default="normal")
    # Whether the document is currently usable. Values: "active", "archived", "deleted".
    # Archived/deleted documents are excluded from search results.
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    # Per-document override for the approval policy. When set, this takes
    # priority over the tenant-wide approval_mode setting. For example, a
    # highly sensitive document can be set to "always" require approval even
    # if the tenant policy is "none". Values: "always", "none", or NULL
    # (meaning "use the tenant-level default").
    approval_override: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    # Where the original file is stored on disk or in cloud storage.
    storage_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    # The user who uploaded this document. Links to the users table.
    created_by: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.user_id"), nullable=False
    )
    # When the document record was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow_naive, nullable=False
    )
    # When the document was last modified (e.g., sensitivity changed).
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow_naive, nullable=False
    )


class TenantPolicy(Base):
    """Stores configuration settings for each tenant's approval workflow.

    This controls whether AI-generated answers need human review before
    being shown to the user. Each tenant can have its own policy.

    approval_mode values:
      - "all"  : Every AI answer must be approved by a reviewer.
      - "sensitive" : Only answers based on sensitive documents need approval.
      - "none" : No approval required — answers are shown immediately.

    Individual documents can override this via their approval_override field.
    """

    __tablename__ = "tenant_policies"

    # The tenant this policy applies to. Also serves as the primary key,
    # meaning each tenant can have at most one policy row.
    tenant_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("tenants.tenant_id"), primary_key=True
    )
    # The approval mode for this tenant. See class docstring for values.
    approval_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="all")
    # When the policy was last changed.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow_naive, nullable=False
    )
    # Who last changed this policy (username or user_id). Can be NULL if
    # the policy was created automatically by the system.
    updated_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
