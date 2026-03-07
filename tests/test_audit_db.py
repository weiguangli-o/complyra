"""Tests for audit_db functions using an in-memory SQLite database."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Approval, AuditLog, IngestJob, Tenant, User, UserTenant
from app.db.session import Base


@pytest.fixture()
def db_session():
    """Create an in-memory SQLite DB with all tables for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = TestSession()
    yield session, TestSession
    session.close()


@pytest.fixture()
def _patch_session(db_session):
    """Patch SessionLocal so audit_db functions use the test DB."""
    _, TestSession = db_session
    with patch("app.db.audit_db.SessionLocal", TestSession):
        yield


class TestInsertLog:
    def test_inserts_log(self, _patch_session, db_session):
        from app.db.audit_db import insert_log

        insert_log(
            tenant_id="t1", user="alice", action="chat",
            input_text="q", output_text="a", metadata="{}",
        )
        session, _ = db_session
        logs = session.query(AuditLog).all()
        assert len(logs) == 1
        assert logs[0].user == "alice"


class TestListLogs:
    def test_returns_filtered_logs(self, _patch_session, db_session):
        from app.db.audit_db import insert_log, list_logs

        insert_log(tenant_id="t1", user="a", action="x", input_text="", output_text="", metadata="")
        insert_log(tenant_id="t2", user="b", action="y", input_text="", output_text="", metadata="")
        result = list_logs(tenant_ids=["t1"], limit=10)
        assert len(result) == 1
        assert result[0].tenant_id == "t1"


class TestSearchLogs:
    def test_search_with_filters(self, _patch_session, db_session):
        from app.db.audit_db import insert_log, search_logs

        insert_log(tenant_id="t1", user="alice", action="chat", input_text="", output_text="", metadata="")
        insert_log(tenant_id="t1", user="bob", action="ingest", input_text="", output_text="", metadata="")

        result = search_logs(tenant_ids=["t1"], username="alice", action=None, start_time=None, end_time=None, limit=10)
        assert len(result) == 1

    def test_search_with_action(self, _patch_session, db_session):
        from app.db.audit_db import insert_log, search_logs

        insert_log(tenant_id="t1", user="a", action="chat", input_text="", output_text="", metadata="")
        insert_log(tenant_id="t1", user="b", action="ingest", input_text="", output_text="", metadata="")

        result = search_logs(tenant_ids=["t1"], username=None, action="ingest", start_time=None, end_time=None, limit=10)
        assert len(result) == 1

    def test_search_with_time_range(self, _patch_session, db_session):
        from app.db.audit_db import insert_log, search_logs

        insert_log(tenant_id="t1", user="a", action="chat", input_text="", output_text="", metadata="")
        result = search_logs(
            tenant_ids=["t1"], username=None, action=None,
            start_time=datetime(2020, 1, 1), end_time=datetime(2030, 1, 1), limit=10,
        )
        assert len(result) == 1


class TestTenantOperations:
    def test_create_tenant(self, _patch_session):
        from app.db.audit_db import create_tenant

        tenant = create_tenant(tenant_id="t1", name="Test")
        assert tenant.tenant_id == "t1"
        assert tenant.name == "Test"

    def test_list_tenants(self, _patch_session):
        from app.db.audit_db import create_tenant, list_tenants

        create_tenant(tenant_id="t1", name="One")
        create_tenant(tenant_id="t2", name="Two")
        result = list_tenants()
        assert len(result) == 2

    def test_get_tenant(self, _patch_session):
        from app.db.audit_db import create_tenant, get_tenant

        create_tenant(tenant_id="t1", name="Test")
        assert get_tenant("t1") is not None
        assert get_tenant("t999") is None


class TestUserOperations:
    def test_create_user(self, _patch_session):
        from app.db.audit_db import create_user

        user = create_user(user_id="u1", username="alice", password_hash="hash", role="admin", default_tenant_id="t1")
        assert user.username == "alice"

    def test_get_user_by_username(self, _patch_session):
        from app.db.audit_db import create_user, get_user_by_username

        create_user(user_id="u1", username="alice", password_hash="h", role="user", default_tenant_id=None)
        assert get_user_by_username("alice") is not None
        assert get_user_by_username("nobody") is None

    def test_get_user_by_id(self, _patch_session):
        from app.db.audit_db import create_user, get_user_by_id

        create_user(user_id="u1", username="alice", password_hash="h", role="user", default_tenant_id=None)
        assert get_user_by_id("u1") is not None
        assert get_user_by_id("u999") is None

    def test_list_users(self, _patch_session):
        from app.db.audit_db import create_user, list_users

        create_user(user_id="u1", username="a", password_hash="h", role="user", default_tenant_id=None)
        create_user(user_id="u2", username="b", password_hash="h", role="admin", default_tenant_id=None)
        assert len(list_users()) == 2


class TestUserTenantOperations:
    def test_assign_user_tenant(self, _patch_session):
        from app.db.audit_db import assign_user_tenant, create_tenant, create_user

        create_tenant(tenant_id="t1", name="T")
        create_user(user_id="u1", username="a", password_hash="h", role="user", default_tenant_id=None)
        link = assign_user_tenant(user_id="u1", tenant_id="t1")
        assert link.user_id == "u1"

    def test_assign_user_tenant_duplicate(self, _patch_session):
        from app.db.audit_db import assign_user_tenant, create_tenant, create_user

        create_tenant(tenant_id="t1", name="T")
        create_user(user_id="u1", username="a", password_hash="h", role="user", default_tenant_id=None)
        assign_user_tenant(user_id="u1", tenant_id="t1")
        existing = assign_user_tenant(user_id="u1", tenant_id="t1")
        assert existing.user_id == "u1"

    def test_list_user_tenants(self, _patch_session):
        from app.db.audit_db import assign_user_tenant, create_tenant, create_user, list_user_tenants

        create_tenant(tenant_id="t1", name="T1")
        create_tenant(tenant_id="t2", name="T2")
        create_user(user_id="u1", username="a", password_hash="h", role="user", default_tenant_id=None)
        assign_user_tenant(user_id="u1", tenant_id="t1")
        assign_user_tenant(user_id="u1", tenant_id="t2")
        assert len(list_user_tenants("u1")) == 2

    def test_user_has_tenant(self, _patch_session):
        from app.db.audit_db import assign_user_tenant, create_tenant, create_user, user_has_tenant

        create_tenant(tenant_id="t1", name="T")
        create_user(user_id="u1", username="a", password_hash="h", role="user", default_tenant_id=None)
        assign_user_tenant(user_id="u1", tenant_id="t1")
        assert user_has_tenant(user_id="u1", tenant_id="t1") is True
        assert user_has_tenant(user_id="u1", tenant_id="t999") is False


class TestApprovalOperations:
    def test_create_approval(self, _patch_session):
        from app.db.audit_db import create_approval

        approval = create_approval(approval_id="a1", user_id="u1", tenant_id="t1", question="q", draft_answer="a")
        assert approval.status == "pending"

    def test_list_approvals(self, _patch_session):
        from app.db.audit_db import create_approval, list_approvals

        create_approval(approval_id="a1", user_id="u1", tenant_id="t1", question="q", draft_answer="a")
        create_approval(approval_id="a2", user_id="u1", tenant_id="t2", question="q", draft_answer="a")
        result = list_approvals(tenant_ids=["t1"], status=None, limit=10)
        assert len(result) == 1

    def test_list_approvals_with_status_filter(self, _patch_session):
        from app.db.audit_db import create_approval, list_approvals

        create_approval(approval_id="a1", user_id="u1", tenant_id="t1", question="q", draft_answer="a")
        result = list_approvals(tenant_ids=["t1"], status="approved", limit=10)
        assert len(result) == 0

    def test_get_approval(self, _patch_session):
        from app.db.audit_db import create_approval, get_approval

        create_approval(approval_id="a1", user_id="u1", tenant_id="t1", question="q", draft_answer="a")
        assert get_approval("a1") is not None
        assert get_approval("a999") is None

    def test_update_approval(self, _patch_session):
        from app.db.audit_db import create_approval, update_approval

        create_approval(approval_id="a1", user_id="u1", tenant_id="t1", question="q", draft_answer="a")
        updated = update_approval(approval_id="a1", status="approved", decision_by="admin", decision_note="ok", final_answer="final")
        assert updated.status == "approved"
        assert updated.final_answer == "final"

    def test_update_approval_not_found(self, _patch_session):
        from app.db.audit_db import update_approval

        result = update_approval(approval_id="a999", status="approved", decision_by="admin", decision_note="ok", final_answer=None)
        assert result is None


class TestIngestJobOperations:
    def test_create_ingest_job(self, _patch_session):
        from app.db.audit_db import create_ingest_job

        job = create_ingest_job(job_id="j1", tenant_id="t1", created_by="u1", filename="doc.pdf")
        assert job.status == "queued"

    def test_update_ingest_job(self, _patch_session):
        from app.db.audit_db import create_ingest_job, update_ingest_job

        create_ingest_job(job_id="j1", tenant_id="t1", created_by="u1", filename="doc.pdf")
        updated = update_ingest_job(job_id="j1", status="completed", chunks_indexed=5, document_id="d1")
        assert updated.status == "completed"
        assert updated.chunks_indexed == 5

    def test_update_ingest_job_not_found(self, _patch_session):
        from app.db.audit_db import update_ingest_job

        result = update_ingest_job(job_id="j999", status="failed")
        assert result is None

    def test_get_ingest_job(self, _patch_session):
        from app.db.audit_db import create_ingest_job, get_ingest_job

        create_ingest_job(job_id="j1", tenant_id="t1", created_by="u1", filename="doc.pdf")
        assert get_ingest_job("j1") is not None
        assert get_ingest_job("j999") is None

    def test_list_ingest_jobs(self, _patch_session):
        from app.db.audit_db import create_ingest_job, list_ingest_jobs

        create_ingest_job(job_id="j1", tenant_id="t1", created_by="u1", filename="a.pdf")
        create_ingest_job(job_id="j2", tenant_id="t2", created_by="u1", filename="b.pdf")
        result = list_ingest_jobs(tenant_ids=["t1"], limit=10)
        assert len(result) == 1


class TestEnsureDefaultSeed:
    def test_seeds_tenant_and_user(self, _patch_session):
        from app.db.audit_db import ensure_default_seed, get_tenant, get_user_by_username

        ensure_default_seed(demo_username="demo", demo_password_hash="hash", default_tenant_id="default")
        assert get_tenant("default") is not None
        assert get_user_by_username("demo") is not None

    def test_idempotent(self, _patch_session):
        from app.db.audit_db import ensure_default_seed, list_users

        ensure_default_seed(demo_username="demo", demo_password_hash="hash", default_tenant_id="default")
        ensure_default_seed(demo_username="demo", demo_password_hash="hash", default_tenant_id="default")
        users = list_users()
        assert len(users) == 1


class TestInitDb:
    def test_init_db_runs(self, _patch_session):
        from app.db.audit_db import init_db

        with patch("app.db.audit_db.Base") as mock_base:
            init_db()
            mock_base.metadata.create_all.assert_called_once()
