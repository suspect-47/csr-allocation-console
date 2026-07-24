"""The agent eval gate (spec §6).

Deterministic. Replays recorded you.com responses against the verify + compose
stages and fails the build if the agents got less trustworthy:

  - any known-bad fixture is marked cleared
  - more than one known-legitimate fixture is marked blocked
  - citation coverage on composed cards is below 100%
  - the impact fabrication guard has been removed

A gate that blocks a merge because the agents drifted is worth more in a demo
than another feature.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.eval.replay import (
    captures_available,
    load_captures,
    load_records,
    record_to_candidate,
    replay_research,
)
from app.flow.compose import compose_card
from app.flow.schemas import CauseStatus, ImpactUnit
from app.flow.state import FlowState, OrgProfile
from app.flow.verify import verify_candidate


@dataclass
class GateResult:
    ok: bool
    failures: list[str] = field(default_factory=list)
    ran: bool = True


def _impact_guard_intact() -> bool:
    # A non-null cost with is_stated=false must be impossible to construct.
    try:
        ImpactUnit(unit_cost=42.0, is_stated=False)
    except ValueError:
        return True
    return False


def run_gate() -> GateResult:
    if not captures_available():
        return GateResult(
            ok=False,
            ran=False,
            failures=[
                "no recorded captures in tests/fixtures/captures/ — the eval gate "
                "cannot run. Record them with live keys: python -m scripts.record_fixtures"
            ],
        )

    failures: list[str] = []
    legit_blocked = 0

    for rec in load_records():
        cand = record_to_candidate(rec)
        state = FlowState(
            run_id="eval",
            org_profile=OrgProfile(
                name="eval", pillars=[rec["pillar"]], geographies=[rec["geography"]],
                quarterly_budget=1.0,
            ),
        )
        with replay_research(load_captures(rec["id"])):
            verdict = verify_candidate(state, cand)

        expected = rec["expected"]
        if expected == "blocked" and verdict.status == CauseStatus.cleared:
            failures.append(f"known-bad fixture '{rec['id']}' was CLEARED")
        if expected == "cleared" and verdict.status == CauseStatus.blocked:
            legit_blocked += 1

        if verdict.status == CauseStatus.cleared:
            try:
                card = compose_card(verdict)
            except ValueError:
                failures.append(f"'{rec['id']}' cleared but citation coverage < 100%")
            else:
                evidence = {c.source_url for c in verdict.checks if c.source_url}
                if any(b.source_url not in evidence for b in card.bullets):
                    failures.append(f"'{rec['id']}' card carries an uncited claim")

    if legit_blocked > 1:
        failures.append(f"{legit_blocked} known-legitimate fixtures blocked (limit is 1)")

    if not _impact_guard_intact():
        failures.append("impact fabrication guard removed: a non-null unstated cost is constructible")

    return GateResult(ok=not failures, failures=failures)
