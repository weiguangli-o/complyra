"""Tests for the Redis queue helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.queue import get_ingest_queue, get_redis_connection


class TestGetRedisConnection:
    @patch("app.services.queue.Redis")
    def test_returns_connection(self, MockRedis):
        get_redis_connection.cache_clear()
        mock_conn = MagicMock()
        MockRedis.from_url.return_value = mock_conn
        conn = get_redis_connection()
        assert conn is mock_conn
        get_redis_connection.cache_clear()


class TestGetIngestQueue:
    @patch("app.services.queue.Queue")
    @patch("app.services.queue.get_redis_connection")
    def test_returns_queue(self, mock_redis, MockQueue):
        get_ingest_queue.cache_clear()
        mock_conn = MagicMock()
        mock_redis.return_value = mock_conn
        mock_q = MagicMock()
        MockQueue.return_value = mock_q
        queue = get_ingest_queue()
        assert queue is mock_q
        get_ingest_queue.cache_clear()
