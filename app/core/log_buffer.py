"""In-memory ring buffer for recent application log entries.

Captures the last N log records for real-time display in the admin
monitoring dashboard without requiring external log infrastructure.

A ring buffer (also called a circular buffer) stores a fixed number of
entries. When the buffer is full and a new entry arrives, the oldest
entry is automatically discarded. Think of it as a conveyor belt of
log messages — you always see the most recent ones, and old ones fall
off the end. This module stores the last 2000 log entries in memory,
which are served by the /logs endpoint in the admin UI.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import List, Optional


@dataclass
class LogEntry:
    """A single log entry stored in the ring buffer.

    This is a simple data container (a Python dataclass) that holds all the
    information about one log message. Each field stores a different piece
    of context:
      - timestamp: when the log was created (Unix epoch seconds)
      - level: severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
      - logger: the name of the Python logger that produced this entry
      - message: the actual log message text
      - request_id: the unique ID of the HTTP request (if applicable)
      - extra: additional key-value pairs like HTTP method, path, etc.
    """

    timestamp: float
    level: str
    logger: str
    message: str
    request_id: str = ""
    extra: dict = field(default_factory=dict)


class LogBuffer:
    """Thread-safe ring buffer that stores the last N log entries in memory for the /logs endpoint.

    "Thread-safe" means multiple parts of the application can add log
    entries at the same time without corrupting the data. This is achieved
    using a lock — only one thread can modify the buffer at a time.

    The underlying data structure is a Python deque with a maximum length.
    When the deque is full, adding a new item automatically removes the
    oldest item from the other end.
    """

    def __init__(self, maxlen: int = 2000):
        """Create a new buffer that holds at most 'maxlen' log entries."""
        self._buffer: deque[LogEntry] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, entry: LogEntry) -> None:
        """Add a new log entry to the buffer (thread-safe).

        If the buffer is already full, the oldest entry is automatically
        discarded to make room.
        """
        with self._lock:
            self._buffer.append(entry)

    def get_entries(
        self,
        limit: int = 100,
        level: Optional[str] = None,
        search: Optional[str] = None,
        since: Optional[float] = None,
    ) -> List[dict]:
        """Retrieve log entries from the buffer with optional filtering.

        Args:
            limit: Maximum number of entries to return (default 100).
            level: If provided, only return entries at this severity level
                   (e.g., "ERROR").
            search: If provided, only return entries whose message or logger
                    name contains this substring (case-insensitive).
            since: If provided, only return entries created after this Unix
                   timestamp.

        Returns:
            A list of dictionaries (most recent entries first), each
            representing one log entry.
        """
        with self._lock:
            entries = list(self._buffer)

        # Apply filters to narrow down the results
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        if level:
            entries = [e for e in entries if e.level == level.upper()]
        if search:
            search_lower = search.lower()
            entries = [
                e
                for e in entries
                if search_lower in e.message.lower() or search_lower in e.logger.lower()
            ]

        # Return most recent first
        entries.reverse()
        return [asdict(e) for e in entries[:limit]]

    def count_by_level(self) -> dict:
        """Count how many entries exist at each severity level.

        Returns a dictionary like {"DEBUG": 10, "INFO": 85, "ERROR": 3, ...}.
        Useful for showing summary statistics in the admin dashboard.
        """
        with self._lock:
            entries = list(self._buffer)
        counts = {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
        for e in entries:
            if e.level in counts:
                counts[e.level] += 1
        return counts


# Global singleton — one shared buffer used by the entire application.
# Using a singleton means all log entries from all parts of the system
# end up in the same buffer, giving a unified view.
_buffer = LogBuffer(maxlen=2000)


def get_log_buffer() -> LogBuffer:
    """Return the global LogBuffer singleton.

    Other modules call this function to access the shared log buffer
    (e.g., the /logs endpoint handler reads from it).
    """
    return _buffer


class BufferHandler(logging.Handler):
    """A Python logging handler that writes log records into the in-memory ring buffer.

    Python's logging system uses "handlers" to decide where log messages go.
    The standard StreamHandler writes to the console; the FileHandler writes
    to a file. This custom handler writes to our in-memory ring buffer so
    that recent logs can be viewed through the admin dashboard without
    needing to access log files or an external logging service.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Convert a standard Python log record into a LogEntry and store it.

        This method is called automatically by the logging system every time
        a log message is produced. It extracts the relevant fields from the
        log record, creates a LogEntry, and appends it to the global buffer.
        """
        entry = LogEntry(
            timestamp=record.created,
            level=record.levelname,
            logger=record.name,
            message=record.getMessage(),
            request_id=getattr(record, "request_id", ""),
            # Pull out specific extra fields that we care about for the
            # admin dashboard display (HTTP method, path, status, etc.)
            extra={
                k: str(v)
                for k, v in record.__dict__.items()
                if k in ("method", "path", "status", "duration_ms", "tenant_id", "user", "action")
                and v is not None
            },
        )
        _buffer.append(entry)
