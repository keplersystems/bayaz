"""Read-only access to `serve.db`.

The database never changes while the process runs, so each worker thread opens its own
connection once and keeps it: no pool, no write path, no transactions.
"""

import sqlite3
import threading
from collections.abc import Sequence
from typing import Any

from bayaz_api import config

_local = threading.local()


def connection() -> sqlite3.Connection:
    existing = getattr(_local, "connection", None)
    if existing is None:
        existing = sqlite3.connect(f"file:{config.SERVE_DB}?mode=ro", uri=True, check_same_thread=False)
        existing.row_factory = sqlite3.Row
        _local.connection = existing
    return existing


def rows(sql: str, parameters: Sequence[Any] = ()) -> list[sqlite3.Row]:
    return connection().execute(sql, tuple(parameters)).fetchall()


def row(sql: str, parameters: Sequence[Any] = ()) -> sqlite3.Row | None:
    return connection().execute(sql, tuple(parameters)).fetchone()


def scalar(sql: str, parameters: Sequence[Any] = ()) -> Any:
    result = row(sql, parameters)
    return result[0] if result else None
