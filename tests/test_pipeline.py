"""End-to-end pure flow: scout → verify → score → compose → allocate (spec §3, §9 step 5).

Patches the you.com client so the whole pipeline runs deterministically offline
without keys or CrewAI. Proves the stages wire together and produce a valid
AllocationSheet from a single discovered, cleared cause.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.clients import youcom
from app.clients.youcom import Citation, ResearchResult, SearchHit, SearchResult
from app.flow.pipeline import run_pipeline
from app.flow.state import FlowState, OrgProfile

RECENT = (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%d")

_UNIVERSAL = ResearchResult(
    answer=(
        f"Help Org is a registered nonprofit, EIN 12-3456789, published {RECENT}. "
        "Donate at helporg.org/donate. No adverse findings."
    ),
    citations=[
        Citation(url="https://helporg.org/about", title="About"),
        Citation(url="https://guidestar.org/helporg", title="GuideStar"),
        Citation(url="https://reuters.com/a", title="Reuters"),
        Citation(url="https://bbc.com/b", title="BBC"),
        Citation(url="https://helporg.org/donate", title="Donate"),
        Citation(url="https://charitynavigator.org/helporg", title="CN"),
    ],
)


@pytest.fixture(autouse=True)
def _patch_youcom(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_search(query: str, **_kw: object) -> SearchResult:
        return SearchResult(hits=[SearchHit(title="Help Org | Donate", url="https://helporg.org/appeal", snippet="urgent unmet need")])

    def fake_research(prompt: str, **_kw: object) -> ResearchResult:
        return _UNIVERSAL

    monkeypatch.setattr(youcom, "search", fake_search)
    monkeypatch.setattr(youcom, "research", fake_research)


def test_full_pipeline_clears_and_allocates() -> None:
    state = FlowState(
        run_id="r1",
        org_profile=OrgProfile(name="Acme", pillars=["Health"], geographies=["Region"], quarterly_budget=100_000.0),
    )
    run_pipeline(state)

    assert len(state.candidates) == 1                      # two searches, same domain, deduped
    assert len(state.cleared_verdicts) == 1
    assert len(state.cards) == 1
    assert state.allocation is not None
    assert len(state.allocation.lines) == 1
    # single cleared cause capped at 40%, remainder visible
    assert state.allocation.lines[0].amount <= 40_000.0 + 1e-6
    assert state.allocation.unallocated > 0
    # score produced no fabricated cost (no unit cost stated in the answer)
    impact = state.impacts[state.candidates[0].source_url]
    assert impact.is_stated is False and impact.unit_cost is None
    # stage timings recorded for the trace
    assert {t.stage for t in state.stage_timings} >= {"scout", "verify", "score", "compose", "allocate"}
