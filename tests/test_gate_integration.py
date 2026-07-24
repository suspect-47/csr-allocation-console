"""End-to-end replay → verify → verdict → compose (spec §6 mechanism).

Uses synthetic ResearchResults fed through the same replay_research context the
eval gate uses. These are test code, not capture files — no fixtures are
written. Proves the gate would clear a legitimate-shaped record, block a bad
one, and keep composed cards fully cited.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.clients.youcom import Citation, ResearchResult
from app.eval.gate import _impact_guard_intact
from app.eval.replay import replay_research
from app.flow.compose import compose_card
from app.flow.schemas import Candidate, CauseStatus, CheckName, NeedType
from app.flow.state import FlowState, OrgProfile
from app.flow.verify import verify_candidate

RECENT = (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%d")


def _state() -> FlowState:
    return FlowState(
        run_id="t",
        org_profile=OrgProfile(name="t", pillars=["Health"], geographies=["Region"], quarterly_budget=1.0),
    )


def _cand() -> Candidate:
    return Candidate(org_name="Help Org", org_domain="helporg.org", claim="urgent need",
                     source_url="https://helporg.org", source_title="Help Org",
                     need_type=NeedType.acute, pillar="Health", geography="Region")


# captures in check order: exists, registration, corroboration, recency, solicitation, contradiction
def _clearing_captures() -> list[ResearchResult]:
    return [
        ResearchResult(answer="Help Org is a registered nonprofit.", citations=[Citation(url="https://helporg.org/about", title="About")]),
        ResearchResult(answer="EIN 12-3456789 is on file.", citations=[Citation(url="https://guidestar.org/helporg", title="GuideStar")]),
        ResearchResult(answer="Reported by multiple outlets.", citations=[Citation(url="https://reuters.com/a"), Citation(url="https://bbc.com/b")]),
        ResearchResult(answer=f"Published {RECENT}.", citations=[Citation(url="https://reuters.com/a")]),
        ResearchResult(answer="Donate on their site.", citations=[Citation(url="https://helporg.org/donate", title="Donate")]),
        ResearchResult(answer="No adverse findings.", citations=[Citation(url="https://charitynavigator.org/helporg")]),
    ]


def _bad_contradiction_captures() -> list[ResearchResult]:
    caps = _clearing_captures()
    caps[5] = ResearchResult(answer="A regulatory complaint alleges fraud.", citations=[Citation(url="https://ag.gov/case")])
    return caps


def test_clearing_record_clears() -> None:
    with replay_research(_clearing_captures()):
        v = verify_candidate(_state(), _cand())
    assert v.status == CauseStatus.cleared
    assert v.blocking_check is None


def test_adverse_signal_blocks_at_contradiction() -> None:
    with replay_research(_bad_contradiction_captures()):
        v = verify_candidate(_state(), _cand())
    assert v.status == CauseStatus.blocked
    assert v.blocking_check == CheckName.contradiction_scan


def test_composed_card_is_fully_cited() -> None:
    with replay_research(_clearing_captures()):
        v = verify_candidate(_state(), _cand())
    card = compose_card(v)
    evidence = {c.source_url for c in v.checks if c.source_url}
    assert len(card.bullets) == 3
    assert all(b.source_url in evidence for b in card.bullets)


def test_impact_guard_is_intact() -> None:
    assert _impact_guard_intact() is True
