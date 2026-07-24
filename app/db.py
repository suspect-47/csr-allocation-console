"""Postgres access via a psycopg3 connection pool.

Thin. Query helpers live next to the code that uses them, not here.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings

_DictConn = Connection[dict[str, Any]]
_pool: ConnectionPool[_DictConn] | None = None


def pool() -> ConnectionPool[_DictConn]:
    global _pool
    if _pool is None:
        # row_factory=dict_row makes rows dict[str, Any]; the generic param tells
        # the type checker the same.
        _pool = ConnectionPool[_DictConn](
            settings.database_url,
            min_size=1,
            max_size=10,
            timeout=5.0,  # fail fast when the DB is down so /healthz stays responsive
            kwargs={"row_factory": dict_row},
            open=True,
        )
    return _pool


@contextmanager
def connection() -> Iterator[Connection[dict[str, Any]]]:
    with pool().connection() as conn:
        yield conn


def fetch_all(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params or {})
        return cur.fetchall()


def fetch_one(sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params or {})
        return cur.fetchone()


def execute(sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Run a write. Returns the RETURNING row when present."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params or {})
        row = cur.fetchone() if cur.description else None
        conn.commit()
        return row


def healthcheck() -> bool:
    row = fetch_one("select 1 as ok")
    return bool(row and row["ok"] == 1)
