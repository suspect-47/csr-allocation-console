"""Typed output for every flow stage.

Each stage returns one of these models. A stage that cannot produce valid
typed output fails the run rather than degrading (spec §3). The rules the
product must never break — no fabricated numbers, cited claims only, the
verdict logic — live here as Pydantic validators, not as prompt instructions.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

# --- enums ------------------------------------------------------------------

class NeedType(StrEnum):
    acute = "acute"
    development = "development"


class CheckName(StrEnum):
    organization_exists = "organization_exists"      # 1
    registration_status = "registration_status"      # 2
    independent_corroboration = "independent_corroboration"  # 3
    recency = "recency"                              # 4
    solicitation_channel = "solicitation_channel"    # 5
    contradiction_scan = "contradiction_scan"        # 6


class CheckOutcome(StrEnum):
    passed = "pass"
    failed = "fail"
    unknown = "unknown"


class CauseStatus(StrEnum):
    cleared = "cleared"
    blocked = "blocked"


# Checks that MUST pass for a cause to clear, and the discretionary trio that
# tolerates at most one unknown between them (spec §3.2 verdict rule).
REQUIRED_PASS: tuple[CheckName, ...] = (
    CheckName.organization_exists,
    CheckName.independent_corroboration,
    CheckName.contradiction_scan,
)
DISCRETIONARY: tuple[CheckName, ...] = (
    CheckName.registration_status,
    CheckName.recency,
    CheckName.solicitation_channel,
)


# --- 3.1 Scout --------------------------------------------------------------

class Candidate(BaseModel):
    org_name: str
    org_domain: str | None = None
    claim: str
    source_url: str
    source_title: str
    need_type: NeedType
    pillar: str
    geography: str


class CandidateList(BaseModel):
    candidates: list[Candidate] = Field(default_factory=list)


# --- 3.2 Verify -------------------------------------------------------------

class CheckResult(BaseModel):
    check_name: CheckName
    result: CheckOutcome
    source_url: str | None = None
    source_title: str | None = None
    excerpt: str = Field(default="", max_length=200)  # store the link, not the article

    @model_validator(mode="after")
    def _no_source_means_unknown(self) -> CheckResult:
        # A check with no source URL is unknown, never pass (spec §3.2).
        if self.result == CheckOutcome.passed and not self.source_url:
            raise ValueError(
                f"{self.check_name.value} marked pass with no source_url; "
                "must be unknown"
            )
        return self


class Verdict(BaseModel):
    candidate: Candidate
    checks: list[CheckResult]
    status: CauseStatus
    blocking_check: CheckName | None = None

    @model_validator(mode="after")
    def _status_matches_checks(self) -> Verdict:
        status, blocking = decide_verdict(self.checks)
        if status != self.status or blocking != self.blocking_check:
            raise ValueError(
                "Verdict status/blocking_check do not match the check results; "
                "use decide_verdict() to derive them"
            )
        return self

    @property
    def has_unknown(self) -> bool:
        return any(c.result == CheckOutcome.unknown for c in self.checks)


class VerdictList(BaseModel):
    verdicts: list[Verdict] = Field(default_factory=list)


def decide_verdict(
    checks: list[CheckResult],
) -> tuple[CauseStatus, CheckName | None]:
    """Apply the spec §3.2 verdict rule.

    cleared requires checks 1, 3, 6 to pass, with at most one unknown across
    2, 4, 5 (and none of 2/4/5 may fail). Anything else is blocked, and the
    first blocking check in check order is named.
    """
    by_name = {c.check_name: c.result for c in checks}

    # Required-pass trio, in check order.
    for name in REQUIRED_PASS:
        if by_name.get(name) != CheckOutcome.passed:
            return CauseStatus.blocked, name

    # Discretionary trio: no fails, at most one unknown.
    unknowns = 0
    for name in DISCRETIONARY:
        outcome = by_name.get(name, CheckOutcome.unknown)
        if outcome == CheckOutcome.failed:
            return CauseStatus.blocked, name
        if outcome == CheckOutcome.unknown:
            unknowns += 1
            if unknowns > 1:
                return CauseStatus.blocked, name

    return CauseStatus.cleared, None


# --- 3.3 Score --------------------------------------------------------------

class ImpactUnit(BaseModel):
    unit_label: str | None = None       # "per family water filter", "per student per term"
    unit_cost: float | None = None
    currency: str | None = None
    is_stated: bool = False             # true only when a source states the unit cost
    stated_by_url: str | None = None

    @model_validator(mode="after")
    def _no_fabricated_cost(self) -> ImpactUnit:
        # A non-null cost must be sourced. Never divide budget by beneficiaries
        # to derive one (spec §3.3). This is the single worst failure mode.
        if self.unit_cost is not None and not self.is_stated:
            raise ValueError("unit_cost is set but is_stated is false (fabricated impact)")
        if self.is_stated and (self.unit_cost is None or not self.stated_by_url):
            raise ValueError("is_stated requires both a unit_cost and a stated_by_url")
        return self


class ImpactList(BaseModel):
    # keyed by candidate source_url to tie back to the cause being scored
    impacts: dict[str, ImpactUnit] = Field(default_factory=dict)


# --- 3.4 Compose ------------------------------------------------------------

class EvidenceBullet(BaseModel):
    text: str
    source_url: str   # every factual claim carries a source_url (spec §3.4)


class Card(BaseModel):
    cause_key: str                       # candidate source_url, ties to evidence
    headline: str = Field(max_length=60)
    summary: str = Field(max_length=240)
    bullets: list[EvidenceBullet] = Field(min_length=3, max_length=3)
    has_unknown: bool = False            # drives hatch texture on the allocation bar

    @model_validator(mode="after")
    def _every_bullet_cited(self) -> Card:
        # Reject any card where a claim lacks a source_url. The evidence-table
        # membership check happens in the compose stage against live rows;
        # here we enforce the shape the validator depends on.
        for b in self.bullets:
            if not b.source_url:
                raise ValueError("evidence bullet has no source_url")
        return self


class CardList(BaseModel):
    cards: list[Card] = Field(default_factory=list)


# --- 3.5 Allocate -----------------------------------------------------------

MAX_SINGLE_CAUSE_SHARE = 0.40
MIN_DEVELOPMENT_SHARE = 0.20


class AllocationLine(BaseModel):
    cause_key: str
    amount: float = Field(ge=0)
    pillar: str
    need_type: NeedType
    rationale: str
    evidence_urls: list[str] = Field(min_length=1)  # cites >=1 evidence row


class AllocationSheet(BaseModel):
    currency: str
    quarterly_budget: float = Field(gt=0)
    lines: list[AllocationLine] = Field(default_factory=list)
    unallocated: float = Field(ge=0)   # remainder stays visible, never forced to 0
    # True when at least one cleared development cause was available to allocate
    # to. The >=20% development floor only binds when there was something to
    # meet it with — a quarter with zero cleared development causes may be all
    # acute rather than fail the run.
    development_available: bool = False

    def allocated_total(self) -> float:
        return round(sum(line.amount for line in self.lines), 2)

    @model_validator(mode="after")
    def _constraints_hold(self) -> AllocationSheet:
        allocated = sum(line.amount for line in self.lines)
        if allocated - self.quarterly_budget > 1e-6:
            raise ValueError("allocated total exceeds quarterly budget")
        if abs(allocated + self.unallocated - self.quarterly_budget) > 1e-6:
            raise ValueError("lines + unallocated must equal quarterly budget")

        cap = self.quarterly_budget * MAX_SINGLE_CAUSE_SHARE
        for line in self.lines:
            if line.amount - cap > 1e-6:
                raise ValueError(
                    f"cause {line.cause_key} exceeds {MAX_SINGLE_CAUSE_SHARE:.0%} cap"
                )

        if self.lines and self.development_available:
            dev = sum(
                line.amount for line in self.lines
                if line.need_type == NeedType.development
            )
            if dev + 1e-6 < self.quarterly_budget * MIN_DEVELOPMENT_SHARE:
                raise ValueError(
                    f"development share below {MIN_DEVELOPMENT_SHARE:.0%} of budget"
                )
        return self
