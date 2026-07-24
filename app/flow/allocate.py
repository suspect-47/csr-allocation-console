"""Allocate stage (spec §3.5).

Constraints enforced in code, not left to the model:
  - cleared causes only
  - no single cause exceeds 40% of budget
  - at least 20% to development when development causes exist
  - every line names its pillar and cites >=1 evidence row
  - the remainder stays unallocated and visible; the bar is never forced to 100%

Budget splits are allocations of the org's own money — not source-stated facts —
so distributing them is allowed. Nothing here fabricates an impact number.
"""

from __future__ import annotations

from app.flow.schemas import (
    MAX_SINGLE_CAUSE_SHARE,
    AllocationLine,
    AllocationSheet,
    CauseStatus,
    NeedType,
    Verdict,
)
from app.flow.state import FlowState

# Leave a visible remainder by default — the bar is not forced to 100%.
_ACUTE_POOL_WITH_DEV = 0.60
_DEV_POOL_WITH_ACUTE = 0.25   # >= the 20% floor, with headroom
_SINGLE_GROUP_POOL = 0.85     # when only one need_type is present


def _evidence_urls(v: Verdict) -> list[str]:
    return [c.source_url for c in v.checks if c.source_url]


def _line(v: Verdict, amount: float) -> AllocationLine:
    cand = v.candidate
    return AllocationLine(
        cause_key=cand.source_url,
        amount=round(amount, 2),
        pillar=cand.pillar,
        need_type=cand.need_type,
        rationale=(
            f"{cand.org_name} cleared verification for {cand.pillar} in "
            f"{cand.geography}; allocation reflects an even split within its "
            f"{cand.need_type.value} pool under the 40% single-cause cap."
        ),
        evidence_urls=_evidence_urls(v),
    )


def _pool_lines(verdicts: list[Verdict], pool_fraction: float, budget: float) -> list[AllocationLine]:
    if not verdicts:
        return []
    cap = budget * MAX_SINGLE_CAUSE_SHARE
    per = min(cap, budget * pool_fraction / len(verdicts))
    return [_line(v, per) for v in verdicts]


def run_allocate(state: FlowState) -> AllocationSheet:
    profile = state.profile()
    budget = profile.quarterly_budget
    cleared = [v for v in state.verdicts if v.status == CauseStatus.cleared and _evidence_urls(v)]

    dev = [v for v in cleared if v.candidate.need_type == NeedType.development]
    acute = [v for v in cleared if v.candidate.need_type == NeedType.acute]

    lines: list[AllocationLine]
    if dev and acute:
        lines = _pool_lines(dev, _DEV_POOL_WITH_ACUTE, budget) + _pool_lines(
            acute, _ACUTE_POOL_WITH_DEV, budget
        )
    elif cleared:
        lines = _pool_lines(cleared, _SINGLE_GROUP_POOL, budget)
    else:
        lines = []

    allocated = round(sum(line.amount for line in lines), 2)
    unallocated = round(budget - allocated, 2)

    return AllocationSheet(
        currency=profile.currency,
        quarterly_budget=budget,
        lines=lines,
        unallocated=unallocated,
        development_available=bool(dev),
    )
