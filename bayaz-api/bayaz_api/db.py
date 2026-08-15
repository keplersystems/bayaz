"""Read-only access to `serve.db`.

The database never changes while the process runs, so there is no write path, no pool to
manage and no transaction handling: each worker thread opens its own connection once and
keeps it. Endpoints are declared `def` rather than `async def`, which puts them on
starlette's thread pool, so sqlite blocking a thread is exactly where the work belongs.
"""

import sqlite3
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Any

_local = threading.local()
_database_path: Path | None = None


def configure(path: Path):
    global _database_path
    if not path.exists():
        raise FileNotFoundError(f"{path}: build it with `bayaz-serving <corpus.db> <serve.db>`")
    _database_path = path


def connection() -> sqlite3.Connection:
    existing = getattr(_local, "connection", None)
    if existing is not None:
        return existing
    if _database_path is None:
        raise RuntimeError("bayaz_api.db.configure() was never called")
    fresh = sqlite3.connect(f"file:{_database_path}?mode=ro", uri=True, check_same_thread=False)
    fresh.row_factory = sqlite3.Row
    fresh.execute("PRAGMA query_only=ON")
    _local.connection = fresh
    return fresh


def rows(sql: str, parameters: Iterable[Any] = ()) -> list[sqlite3.Row]:
    return connection().execute(sql, tuple(parameters)).fetchall()


def row(sql: str, parameters: Iterable[Any] = ()) -> sqlite3.Row | None:
    return connection().execute(sql, tuple(parameters)).fetchone()


def scalar(sql: str, parameters: Iterable[Any] = ()) -> Any:
    result = row(sql, parameters)
    return result[0] if result else None
