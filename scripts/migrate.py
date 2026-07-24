"""Apply SQL migrations in order, once each. Idempotent.

    python -m scripts.migrate

Tracks applied files in schema_migrations. No ORM, no framework — the schema
is small and SQL is clearer than a migration DSL here.
"""

from __future__ import annotations

import sys
from pathlib import Path

from app import db

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def _ensure_tracking_table() -> None:
    db.execute(
        """
        create table if not exists schema_migrations (
            filename   text primary key,
            applied_at timestamptz not null default now()
        )
        """
    )


def _applied() -> set[str]:
    rows = db.fetch_all("select filename from schema_migrations")
    return {r["filename"] for r in rows}


def run() -> int:
    _ensure_tracking_table()
    done = _applied()
    files = sorted(p for p in MIGRATIONS_DIR.glob("*.sql"))
    applied = 0
    for path in files:
        if path.name in done:
            continue
        sql = path.read_text()
        with db.connection() as conn, conn.cursor() as cur:
            cur.execute(sql)
            cur.execute(
                "insert into schema_migrations (filename) values (%(f)s)",
                {"f": path.name},
            )
            conn.commit()
        print(f"applied {path.name}")
        applied += 1
    if applied == 0:
        print("no pending migrations")
    return 0


if __name__ == "__main__":
    sys.exit(run())
