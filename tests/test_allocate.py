"""Allocation constraints hold under the deterministic allocator (spec §3.5)."""

from __future__ import annotations

from app.flow.allocate import run_allocate
from app.flow.schemas import (
    Candidate,
    CauseStatus,
    CheckName,
    CheckOutcome,
    CheckResult,
    NeedType,
    Verdict,
)
from app.flow.state import FlowState, OrgProfile


def _cleared(key: str, need: NeedType) -> Verdict:
    cand = Candidate(org_name=key, org_domain=f"{key}.org", claim="need",
                     source_url=f"https://{key}.org", source_title=key,
                     need_type=need, pillar="Health", geography="Region")
    checks = [CheckResult(check_name=n, result=CheckOutcome.passed,
                          source_url=f"https://{key}.org/e", source_title="e", excerpt="x")
              for n in CheckName]
    return Verdict(candidate=cand, checks=checks, status=CauseStatus.cleared, blocking_check=None)


def _state(verdicts: list[Verdict], budget: float = 100_000.0) -> FlowState:
    profile = OrgProfile(name="Acme", pillars=["Health"], geographies=["Region"],
                         quarterly_budget=budget, currency="USD")
    return FlowState(run_id="r", org_profile=profile, verdicts=verdicts)


def test_cap_and_dev_floor_with_mixed_causes() -> None:
    verdicts = [_cleared("dev1", NeedType.development), _cleared("acute1", NeedType.acute),
                _cleared("acute2", NeedType.acute)]
    sheet = run_allocate(_state(verdicts))
    budget = 100_000.0
    # 40% cap holds
    assert all(line.amount <= budget * 0.40 + 1e-6 for line in sheet.lines)
    # development floor holds (>=20%)
    dev = sum(line.amount for line in sheet.lines if line.need_type == NeedType.development)
    assert dev + 1e-6 >= budget * 0.20
    # remainder visible and non-negative
    assert sheet.unallocated >= 0
    assert sheet.allocated_total() + sheet.unallocated == budget
    # every line cites evidence
    assert all(line.evidence_urls for line in sheet.lines)


def test_single_cleared_capped_at_40pct() -> None:
    sheet = run_allocate(_state([_cleared("solo", NeedType.acute)]))
    assert sheet.lines[0].amount <= 100_000.0 * 0.40 + 1e-6
    assert sheet.unallocated > 0  # not forced to 100%


def test_all_acute_does_not_require_dev_floor() -> None:
    verdicts = [_cleared("a1", NeedType.acute), _cleared("a2", NeedType.acute)]
    sheet = run_allocate(_state(verdicts))
    assert sheet.development_available is False
    assert sheet.allocated_total() > 0


def test_no_cleared_leaves_budget_unallocated() -> None:
    sheet = run_allocate(_state([]))
    assert sheet.lines == []
    assert sheet.unallocated == 100_000.0
