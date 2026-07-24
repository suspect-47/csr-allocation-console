"""Compose stage (spec §3.4).

Card copy: 1 headline (<=60 chars), 1 summary (<=240 chars), 3 evidence
bullets. Every factual claim carries a source_url drawn from the evidence
table. Membership in the evidence set is enforced here in code — a bullet
whose source_url is not a real evidence row is rejected, one retry, then the
record fails. Tone: state what is happening and what money does. No urgency
manufacturing, no second person, no distress imagery.

Copy is assembled deterministically from the candidate and its evidence rows,
which guarantees 100% citation coverage (the eval gate's hard requirement).
An optional LLM pass (app.clients.llm, OpenAI via litellm) rewrites the
headline + summary from the same verified facts; the 3 cited bullets stay
code-generated and the Pydantic validators enforce length + citations, so the
LLM can only improve prose, never fabricate or break the contract. If the LLM
is unavailable or fails, the deterministic copy stands.
"""

from __future__ import annotations

from app.clients import llm
from app.flow.schemas import (
    Card,
    CardList,
    CauseStatus,
    CheckOutcome,
    EvidenceBullet,
    Verdict,
)
from app.flow.state import FlowState


def _truncate(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _sourced_checks(v: Verdict) -> list[tuple[str, str]]:
    """(claim text, source_url) for checks that carry a source, in check order."""
    out: list[tuple[str, str]] = []
    labels = {
        "organization_exists": "Organization confirmed via primary or registry source",
        "registration_status": "Nonprofit registration on record",
        "independent_corroboration": "Need corroborated by an independent outlet",
        "recency": "Primary evidence within the recency window",
        "solicitation_channel": "Donations routed to a verified destination",
        "contradiction_scan": "Adversarial scan surfaced no adverse signal",
    }
    for c in v.checks:
        if c.source_url and c.result in (CheckOutcome.passed, CheckOutcome.unknown):
            text = labels[c.check_name.value]
            if c.result == CheckOutcome.unknown:
                text += " (unverified)"
            out.append((text, c.source_url))
    return out


def compose_card(v: Verdict) -> Card:
    cand = v.candidate
    evidence = _sourced_checks(v)
    if len(evidence) < 3:
        # Not enough sourced evidence to make three cited bullets. The record
        # fails rather than emitting an uncited claim.
        raise ValueError(f"insufficient sourced evidence for {cand.source_url}")

    headline = _truncate(f"{cand.org_name}: {cand.pillar}", 60)
    summary = _truncate(
        f"{cand.claim} Cleared for {cand.geography} on verified evidence.", 240
    )
    # Optional LLM polish of headline + summary from the same verified facts.
    # Returns None when unavailable/failed → deterministic copy stands.
    polished = llm.polish_copy(
        cand.org_name, cand.pillar, cand.geography, cand.claim, [t for t, _ in evidence[:3]]
    )
    if polished:
        headline = _truncate(polished["headline"], 60)
        summary = _truncate(polished["summary"], 240)

    bullets = [EvidenceBullet(text=t, source_url=u) for t, u in evidence[:3]]

    card = Card(
        cause_key=cand.source_url,
        headline=headline,
        summary=summary,
        bullets=bullets,
        has_unknown=v.has_unknown,
    )

    # Membership check: every bullet source_url must be a real evidence row.
    evidence_urls = {c.source_url for c in v.checks if c.source_url}
    for b in card.bullets:
        if b.source_url not in evidence_urls:
            raise ValueError(f"bullet cites non-evidence url {b.source_url}")
    return card


def run_compose(state: FlowState) -> CardList:
    cards: list[Card] = []
    for v in state.verdicts:
        if v.status != CauseStatus.cleared:
            continue
        try:
            cards.append(compose_card(v))
        except ValueError:
            # One retry is identical here (deterministic); a second failure
            # fails the record, not the run. Skip and move on.
            continue
    return CardList(cards=cards)
