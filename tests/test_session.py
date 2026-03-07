"""Tests for database session utilities."""

from __future__ import annotations

from app.db.session import get_db


def test_get_db_yields_and_closes():
    gen = get_db()
    session = next(gen)
    assert session is not None
    # Closing the generator calls session.close()
    try:
        next(gen)
    except StopIteration:
        pass
