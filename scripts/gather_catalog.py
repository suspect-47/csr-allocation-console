"""Gather a real, image-rich org catalog + events from you.com Search.

Populates the marketplace with real charities and their imagery (you.com
thumbnail + favicon) across pillars. These are stored as status='listed' — real
orgs surfaced from top-charity searches, each carrying its source, but not run
through the full 6-check pipeline (that stays the 'cleared' tier). Also backfills
imagery for already-cleared causes and gathers a few live events.

    python -m scripts.gather_catalog
"""

from __future__ import annotations

import sys

from app import db
from app.clients import llm, youcom
from app.clients.youcom import Freshness
from app.flow.scout import is_org_domain, org_name_from_domain, registrable_domain

PILLARS: dict[str, str] = {
    "Clean Water": "top clean water and sanitation charities nonprofits to donate",
    "Education": "top education charities nonprofits for children to donate",
    "Health": "top global health and medical relief charities nonprofits to donate",
    "Food Security": "top hunger and food security charities nonprofits to donate",
    "Disaster Relief": "top disaster relief humanitarian charities nonprofits to donate",
    "Poverty Relief": "top poverty relief and cash transfer charities nonprofits to donate",
    "Environment": "top environmental conservation and climate charities nonprofits to donate",
    "Animals": "top animal welfare and wildlife conservation charities nonprofits to donate",
    "Refugees": "top refugee and migrant aid charities nonprofits to donate",
    "Mental Health": "top mental health support charities nonprofits to donate",
}
PER_PILLAR = 12


def _existing_domains() -> set[str]:
    return {r["org_domain"] for r in db.fetch_all(
        "select org_domain from causes where org_domain is not null") if r["org_domain"]}


def gather_catalog() -> int:
    seen = _existing_domains()
    added = 0
    for pillar, query in PILLARS.items():
        res = youcom.search(query, freshness=Freshness.year, count=15)
        count = 0
        for hit in res.hits:
            if count >= PER_PILLAR:
                break
            domain = registrable_domain(hit.url)
            if not domain or not is_org_domain(domain) or domain in seen:
                continue
            desc = llm.describe_org(hit.title, domain, hit.snippet)
            if desc is None:
                if llm.available():
                    continue  # LLM judged it not a single charity
                desc = {"name": org_name_from_domain(domain), "blurb": (hit.snippet or "")[:120]}
            seen.add(domain)
            name = desc["name"]
            blurb = desc.get("blurb") or f"{name} works on {pillar.lower()}."
            row = db.execute(
                """
                insert into causes
                    (org_name, org_domain, headline, summary, blurb, geography, pillar,
                     need_type, status, image_url, logo_url, created_at)
                values
                    (%(n)s, %(d)s, %(h)s, %(s)s, %(b)s, 'Global', %(p)s,
                     'development', 'listed', %(img)s, %(logo)s, now())
                returning id
                """,
                {"n": name, "d": domain, "h": blurb,
                 "s": f"{name} · {pillar}. Listed from a top-charity directory; full verification pending.",
                 "b": blurb, "p": pillar,
                 "img": hit.thumbnail or None, "logo": hit.favicon or None},
            )
            assert row is not None
            db.execute(
                """
                insert into evidence (cause_id, check_name, result, source_url, source_title, excerpt, retrieved_at)
                values (%(c)s, 'directory_listing', 'pass', %(u)s, %(t)s, %(e)s, now())
                """,
                {"c": row["id"], "u": hit.url, "t": hit.title, "e": (hit.snippet or "")[:200]},
            )
            added += 1
            count += 1
        print(f"  {pillar}: +{count}", flush=True)
    return added


def backfill_images() -> int:
    """Give already-cleared causes real imagery from a targeted search."""
    rows = db.fetch_all("select id, org_name, org_domain, pillar from causes where image_url is null")
    n = 0
    for r in rows:
        res = youcom.search(f"{r['org_name']} {r['pillar']} charity", freshness=Freshness.year, count=5)
        pick = next((h for h in res.hits if registrable_domain(h.url) == r["org_domain"]), None) or (res.hits[0] if res.hits else None)
        if pick and (pick.thumbnail or pick.favicon):
            db.execute("update causes set image_url = %(i)s, logo_url = %(l)s where id = %(id)s",
                       {"i": pick.thumbnail or None, "l": pick.favicon or None, "id": r["id"]})
            n += 1
    return n


def gather_events() -> int:
    n = 0
    for pillar in PILLARS:
        res = youcom.search(f"{pillar} charity fundraiser campaign 2026 event", freshness=Freshness.month, count=6)
        picks = [h for h in res.hits if is_org_domain(registrable_domain(h.url))][:2]
        for h in picks:
            title = h.title.split(" | ")[0].split(" - ")[0][:80]
            db.execute(
                """insert into events (title, pillar, geography, status, source_url, source_title)
                   values (%(t)s, %(p)s, 'Global', 'live', %(u)s, %(st)s)""",
                {"t": title, "p": pillar, "u": h.url, "st": h.title},
            )
            n += 1
    return n


def main() -> int:
    print("gathering catalog...", flush=True)
    c = gather_catalog()
    print(f"catalog: +{c} orgs", flush=True)
    b = backfill_images()
    print(f"backfilled images: {b}", flush=True)
    e = gather_events()
    print(f"events: +{e}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
