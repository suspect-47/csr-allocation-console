"""Database reads and writes for the six tables (spec §4).

Every cause persisted here arrived through the pipeline and carries an evidence
chain — blocked causes included. A cause with no evidence rows is a bug. There
is no path in this module that inserts a cause without its checks.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from app import db
from app.flow.compose import _truncate
from app.flow.schemas import CauseStatus
from app.flow.state import FlowState, OrgProfile


def _now() -> datetime:
    return datetime.now(UTC)


# --- org profiles -----------------------------------------------------------

def create_profile(p: OrgProfile) -> str:
    row = db.execute(
        """
        insert into org_profiles (name, pillars, geographies, quarterly_budget, currency)
        values (%(name)s, %(pillars)s, %(geographies)s, %(budget)s, %(currency)s)
        returning id
        """,
        {
            "name": p.name,
            "pillars": p.pillars,
            "geographies": p.geographies,
            "budget": p.quarterly_budget,
            "currency": p.currency,
        },
    )
    assert row is not None
    return str(row["id"])


def get_profile(profile_id: str) -> OrgProfile | None:
    row = db.fetch_one("select * from org_profiles where id = %(id)s", {"id": profile_id})
    return _row_to_profile(row) if row else None


def active_profiles() -> list[OrgProfile]:
    rows = db.fetch_all("select * from org_profiles order by created_at")
    return [_row_to_profile(r) for r in rows]


def _row_to_profile(row: dict[str, Any]) -> OrgProfile:
    return OrgProfile(
        id=str(row["id"]),
        name=row["name"],
        pillars=list(row["pillars"]),
        geographies=list(row["geographies"]),
        quarterly_budget=float(row["quarterly_budget"]),
        currency=row["currency"],
    )


# --- runs -------------------------------------------------------------------

def create_run() -> str:
    run_id = str(uuid.uuid4())
    db.execute(
        "insert into runs (id, status, started_at) values (%(id)s, 'queued', %(t)s)",
        {"id": run_id, "t": _now()},
    )
    return run_id


def set_run_status(run_id: str, status: str) -> None:
    db.execute(
        "update runs set status = %(s)s where id = %(id)s",
        {"s": status, "id": run_id},
    )


def finish_run(run_id: str, state: FlowState, status: str) -> None:
    cleared = sum(1 for v in state.verdicts if v.status == CauseStatus.cleared)
    db.execute(
        """
        update runs set
            status = %(status)s,
            finished_at = %(t)s,
            stage_timings = %(timings)s,
            found = %(found)s,
            cleared = %(cleared)s,
            blocked = %(blocked)s,
            tool_calls = %(tool_calls)s
        where id = %(id)s
        """,
        {
            "status": status,
            "t": _now(),
            "timings": json.dumps([st.model_dump() for st in state.stage_timings]),
            "found": len(state.candidates),
            "cleared": cleared,
            "blocked": len(state.verdicts) - cleared,
            "tool_calls": state.tool_calls,
            "id": run_id,
        },
    )


# --- causes / evidence / impact / allocations -------------------------------

def persist_results(run_id: str, state: FlowState) -> None:
    """Write every verdict as a cause + its evidence chain, then the sheet.

    Runs in one transaction so a run never leaves half-written causes.
    """
    profile = state.profile()
    cards = {c.cause_key: c for c in state.cards}

    with db.connection() as conn, conn.cursor() as cur:
        cause_ids: dict[str, str] = {}
        for v in state.verdicts:
            cand = v.candidate
            card = cards.get(cand.source_url)
            headline = card.headline if card else _truncate(f"{cand.org_name}: {cand.pillar}", 60)
            summary = card.summary if card else _truncate(cand.claim, 240)

            cur.execute(
                """
                insert into causes
                    (org_name, org_domain, headline, summary, geography, pillar,
                     need_type, status, blocking_check, created_at)
                values
                    (%(org_name)s, %(org_domain)s, %(headline)s, %(summary)s,
                     %(geography)s, %(pillar)s, %(need_type)s, %(status)s,
                     %(blocking_check)s, %(t)s)
                returning id
                """,
                {
                    "org_name": cand.org_name,
                    "org_domain": cand.org_domain,
                    "headline": headline,
                    "summary": summary,
                    "geography": cand.geography,
                    "pillar": cand.pillar,
                    "need_type": cand.need_type.value,
                    "status": v.status.value,
                    "blocking_check": v.blocking_check.value if v.blocking_check else None,
                    "t": _now(),
                },
            )
            fetched = cur.fetchone()
            assert fetched is not None
            cause_id = str(fetched["id"])
            cause_ids[cand.source_url] = cause_id

            for chk in v.checks:
                cur.execute(
                    """
                    insert into evidence
                        (cause_id, check_name, result, source_url, source_title,
                         excerpt, retrieved_at)
                    values
                        (%(cause_id)s, %(check_name)s, %(result)s, %(source_url)s,
                         %(source_title)s, %(excerpt)s, %(t)s)
                    """,
                    {
                        "cause_id": cause_id,
                        "check_name": chk.check_name.value,
                        "result": chk.result.value,
                        "source_url": chk.source_url,
                        "source_title": chk.source_title,
                        "excerpt": chk.excerpt,
                        "t": _now(),
                    },
                )

            impact = state.impacts.get(cand.source_url)
            if impact is not None:
                cur.execute(
                    """
                    insert into impact_units
                        (cause_id, unit_label, unit_cost, currency, is_stated, stated_by_url)
                    values
                        (%(cause_id)s, %(unit_label)s, %(unit_cost)s, %(currency)s,
                         %(is_stated)s, %(stated_by_url)s)
                    """,
                    {
                        "cause_id": cause_id,
                        "unit_label": impact.unit_label,
                        "unit_cost": impact.unit_cost,
                        "currency": impact.currency,
                        "is_stated": impact.is_stated,
                        "stated_by_url": impact.stated_by_url,
                    },
                )

        if state.allocation is not None:
            for line in state.allocation.lines:
                alloc_cause_id = cause_ids.get(line.cause_key)
                if alloc_cause_id is None:
                    continue
                cur.execute(
                    """
                    insert into allocations
                        (org_profile_id, cause_id, amount, rationale, created_at)
                    values
                        (%(profile_id)s, %(cause_id)s, %(amount)s, %(rationale)s, %(t)s)
                    """,
                    {
                        "profile_id": profile.id,
                        "cause_id": alloc_cause_id,
                        "amount": line.amount,
                        "rationale": line.rationale,
                        "t": _now(),
                    },
                )
        conn.commit()


# --- reads for the web API --------------------------------------------------

def cleared_cards() -> list[dict[str, Any]]:
    return db.fetch_all(
        """
        select c.id, c.org_name, c.org_domain, c.headline, c.summary, c.geography,
               c.pillar, c.need_type,
               exists(select 1 from evidence e
                      where e.cause_id = c.id and e.result = 'unknown') as has_unknown,
               (select a.amount from allocations a
                where a.cause_id = c.id order by a.created_at desc limit 1) as amount
        from causes c
        where c.status = 'cleared'
        order by c.created_at desc
        """
    )


def blocked_causes() -> list[dict[str, Any]]:
    return db.fetch_all(
        """
        select id, org_name, headline, summary, geography, pillar, need_type,
               blocking_check, created_at
        from causes where status = 'blocked'
        order by created_at desc
        """
    )


def cause_detail(cause_id: str) -> dict[str, Any] | None:
    cause = db.fetch_one("select * from causes where id = %(id)s", {"id": cause_id})
    if cause is None:
        return None
    evidence = db.fetch_all(
        "select check_name, result, source_url, source_title, excerpt, retrieved_at "
        "from evidence where cause_id = %(id)s order by check_name",
        {"id": cause_id},
    )
    impact = db.fetch_one(
        "select unit_label, unit_cost, currency, is_stated, stated_by_url "
        "from impact_units where cause_id = %(id)s",
        {"id": cause_id},
    )
    return {"cause": cause, "evidence": evidence, "impact": impact}


def list_runs(limit: int = 25) -> list[dict[str, Any]]:
    return db.fetch_all(
        "select id, status, started_at, finished_at, found, cleared, blocked, tool_calls "
        "from runs order by started_at desc limit %(limit)s",
        {"limit": limit},
    )


def get_run(run_id: str) -> dict[str, Any] | None:
    return db.fetch_one("select * from runs where id = %(id)s", {"id": run_id})
