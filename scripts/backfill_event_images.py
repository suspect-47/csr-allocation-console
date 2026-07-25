"""Backfill real event thumbnails from you.com Search (one image per event
title). Idempotent — only touches events with a null image_url.

    set -a; . ./.env; set +a
    .venv/bin/python -m scripts.backfill_event_images
"""

from __future__ import annotations

from app import db
from app.clients import youcom


def _query(title: str) -> str:
    # trim trailing qualifiers so the search matches the event, not the suffix
    q = title.split(" — ")[0].split(":")[0].strip()
    return q or title


def main() -> None:
    rows = db.fetch_all(
        "select id, title from events where image_url is null order by created_at desc"
    )
    print(f"{len(rows)} events need images")
    for r in rows:
        q = _query(r["title"])
        try:
            res = youcom.search(q, freshness="year", count=6)
        except Exception as e:  # noqa: BLE001 — best-effort backfill
            print(f"  skip  {q!r}: {e}")
            continue
        hits = list(res.news) + list(res.hits)
        thumb = next((h.thumbnail for h in hits if h.thumbnail), None)
        if not thumb:
            print(f"  none  {q!r}")
            continue
        with db.connection() as conn, conn.cursor() as cur:
            cur.execute("update events set image_url = %s where id = %s", (thumb, r["id"]))
        print(f"  ok    {q!r} -> {thumb[:70]}")


if __name__ == "__main__":
    main()
