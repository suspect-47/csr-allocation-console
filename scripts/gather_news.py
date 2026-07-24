"""Gather news + video for the News tab from you.com Search.

Articles come from you.com news results (with imagery); videos from a
youtube.com-scoped search (the video id yields a standard thumbnail). Real,
per-pillar, deduped by URL.

    python -m scripts.gather_news
"""

from __future__ import annotations

import sys
from urllib.parse import parse_qs, urlparse

from app import db
from app.clients import youcom
from app.clients.youcom import Freshness

PILLARS = ["Clean Water", "Education", "Health", "Food Security", "Disaster Relief", "Poverty Relief"]


def yt_id(url: str) -> str | None:
    try:
        u = urlparse(url)
        if "youtu.be" in u.netloc:
            return u.path.strip("/").split("/")[0] or None
        if "youtube.com" in u.netloc:
            if u.path.startswith("/watch"):
                return parse_qs(u.query).get("v", [None])[0]
            for pre in ("/embed/", "/shorts/", "/v/"):
                if u.path.startswith(pre):
                    return u.path.split(pre)[1].split("/")[0]
    except Exception:  # noqa: BLE001
        return None
    return None


def source_of(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:  # noqa: BLE001
        return "source"


def gather_articles() -> int:
    total = 0
    for pillar in PILLARS:
        res = youcom.search(f"{pillar} charity nonprofit humanitarian news", freshness=Freshness.month, count=12)
        items = res.news or res.hits
        c = 0
        for h in items:
            if c >= 5:
                break
            if not h.url or not h.title:
                continue
            row = db.execute(
                """
                insert into news_items (kind, title, source, url, image_url, excerpt, published, pillar)
                values ('article', %(t)s, %(s)s, %(u)s, %(img)s, %(e)s, %(p)s, %(pil)s)
                on conflict (url) do nothing returning id
                """,
                {"t": h.title[:200], "s": source_of(h.url), "u": h.url, "img": h.thumbnail or None,
                 "e": (h.snippet or "")[:280], "p": h.date or None, "pil": pillar},
            )
            if row:
                total += 1
                c += 1
        print(f"  articles {pillar}: {c}", flush=True)
    return total


def gather_videos() -> int:
    total = 0
    for pillar in PILLARS:
        res = youcom.search(f"{pillar} charity nonprofit", include_domains=["youtube.com"], count=6)
        c = 0
        for h in res.hits:
            if c >= 2:
                break
            vid = yt_id(h.url)
            if not vid:
                continue
            row = db.execute(
                """
                insert into news_items (kind, title, source, url, image_url, excerpt, pillar, video_id)
                values ('video', %(t)s, 'YouTube', %(u)s, %(img)s, %(e)s, %(pil)s, %(vid)s)
                on conflict (url) do nothing returning id
                """,
                {"t": h.title[:200], "u": h.url, "img": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                 "e": (h.snippet or "")[:200], "pil": pillar, "vid": vid},
            )
            if row:
                total += 1
                c += 1
        print(f"  videos {pillar}: {c}", flush=True)
    return total


def main() -> int:
    print("gathering news...", flush=True)
    a = gather_articles()
    print(f"articles: +{a}", flush=True)
    v = gather_videos()
    print(f"videos: +{v}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
