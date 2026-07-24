"""Schema round-trips + the rules that must never break (spec §3, §9 step 3)."""

from __future__ import annotations

import pytest
from app.flow.schemas import (
    AllocationLine,
    AllocationSheet,
    Candidate,
    Card,
    CauseStatus,
    CheckName,
    CheckOutcome,
    CheckResult,
    EvidenceBullet,
    ImpactUnit,
    NeedType,
    Verdict,
    decide_verdict,
)
from pydantic import ValidationError


def _passing(name: CheckName) -> CheckResult:
    return CheckResult(check_name=name, result=CheckOutcome.passed,
                       source_url="https://ex.org", source_title="t", excerpt="e")


def _unknown(name: CheckName) -> CheckResult:
    return CheckResult(check_name=name, result=CheckOutcome.unknown, excerpt="e")


def _fail(name: CheckName) -> CheckResult:
    return CheckResult(check_name=name, result=CheckOutcome.failed, excerpt="e")


def _all_checks(overrides: dict[CheckName, CheckResult] | None = None) -> list[CheckResult]:
    base = {n: _passing(n) for n in CheckName}
    if overrides:
        base.update(overrides)
    return list(base.values())


def test_check_pass_requires_source() -> None:
    with pytest.raises(ValidationError):
        CheckResult(check_name=CheckName.recency, result=CheckOutcome.passed, source_url=None)


def test_verdict_all_pass_clears() -> None:
    status, blocking = decide_verdict(_all_checks())
    assert status == CauseStatus.cleared
    assert blocking is None


def test_verdict_one_unknown_in_discretionary_clears() -> None:
    checks = _all_checks({CheckName.recency: _unknown(CheckName.recency)})
    status, blocking = decide_verdict(checks)
    assert status == CauseStatus.cleared


def test_verdict_two_unknowns_blocks() -> None:
    checks = _all_checks({
        CheckName.recency: _unknown(CheckName.recency),
        CheckName.registration_status: _unknown(CheckName.registration_status),
    })
    status, blocking = decide_verdict(checks)
    assert status == CauseStatus.blocked
    assert blocking in {CheckName.recency, CheckName.registration_status}


def test_verdict_required_fail_blocks_and_names_check() -> None:
    checks = _all_checks({CheckName.contradiction_scan: _fail(CheckName.contradiction_scan)})
    status, blocking = decide_verdict(checks)
    assert status == CauseStatus.blocked
    assert blocking == CheckName.contradiction_scan


def test_verdict_discretionary_fail_blocks() -> None:
    checks = _all_checks({CheckName.solicitation_channel: _fail(CheckName.solicitation_channel)})
    status, _ = decide_verdict(checks)
    assert status == CauseStatus.blocked


def test_impact_unit_rejects_fabricated_cost() -> None:
    with pytest.raises(ValidationError):
        ImpactUnit(unit_cost=40.0, is_stated=False)


def test_impact_unit_stated_needs_source() -> None:
    with pytest.raises(ValidationError):
        ImpactUnit(unit_cost=40.0, is_stated=True, stated_by_url=None)
    ok = ImpactUnit(unit_cost=40.0, is_stated=True, stated_by_url="https://ex.org", unit_label="per kit")
    assert ok.unit_cost == 40.0


def test_card_requires_three_cited_bullets() -> None:
    bullets = [EvidenceBullet(text=f"b{i}", source_url="https://ex.org") for i in range(3)]
    card = Card(cause_key="k", headline="h", summary="s", bullets=bullets)
    assert len(card.bullets) == 3
    with pytest.raises(ValidationError):
        Card(cause_key="k", headline="h", summary="s", bullets=bullets[:2])


def test_allocation_cap_enforced() -> None:
    line = AllocationLine(cause_key="k", amount=60, pillar="p", need_type=NeedType.acute,
                          rationale="r", evidence_urls=["https://ex.org"])
    with pytest.raises(ValidationError):
        AllocationSheet(currency="USD", quarterly_budget=100, lines=[line], unallocated=40)


def test_allocation_development_floor_when_available() -> None:
    acute = AllocationLine(cause_key="a", amount=30, pillar="p", need_type=NeedType.acute,
                           rationale="r", evidence_urls=["https://ex.org"])
    with pytest.raises(ValidationError):
        AllocationSheet(currency="USD", quarterly_budget=100, lines=[acute], unallocated=70,
                        development_available=True)


def test_allocation_remainder_visible_ok() -> None:
    a = AllocationLine(cause_key="a", amount=25, pillar="p", need_type=NeedType.development,
                       rationale="r", evidence_urls=["https://ex.org"])
    b = AllocationLine(cause_key="b", amount=30, pillar="p", need_type=NeedType.acute,
                       rationale="r", evidence_urls=["https://ex.org"])
    sheet = AllocationSheet(currency="USD", quarterly_budget=100, lines=[a, b],
                            unallocated=45, development_available=True)
    assert sheet.unallocated == 45
    assert sheet.allocated_total() == 55


def test_roundtrip_all_stage_models() -> None:
    cand = Candidate(org_name="Org", org_domain="org.org", claim="need", source_url="https://org.org",
                     source_title="Org", need_type=NeedType.acute, pillar="Water", geography="Kenya")
    verdict = Verdict(candidate=cand, checks=_all_checks(), status=CauseStatus.cleared, blocking_check=None)
    for model in (cand, verdict):
        clone = type(model).model_validate_json(model.model_dump_json())
        assert clone == model
