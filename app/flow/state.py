"""Flow state — one Pydantic BaseModel threaded through every stage (spec §3).

The CrewAI Flow reads and writes this. Each stage appends its typed output.
Nothing here estimates or fills a number a source did not state.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.flow.schemas import (
    AllocationSheet,
    Candidate,
    Card,
    ImpactUnit,
    NeedType,
    Verdict,
)


class OrgProfile(BaseModel):
    """The corporate giving profile. Created via the setup form on first run."""

    id: str | None = None
    name: str
    pillars: list[str] = Field(min_length=1)
    geographies: list[str] = Field(min_length=1)
    quarterly_budget: float = Field(gt=0)
    currency: str = "USD"

    def query_pairs(self) -> list[tuple[str, str]]:
        """One (pillar, geography) pair per Scout query (spec §3.1)."""
        return [(p, g) for p in self.pillars for g in self.geographies]


class StageTiming(BaseModel):
    stage: str
    ms: float


class FlowState(BaseModel):
    # inputs — defaulted so CrewAI can auto-instantiate the structured state;
    # the worker sets both to real values before kickoff (see flow.pipeline).
    run_id: str = ""
    org_profile: OrgProfile | None = None

    # per-stage accumulators
    candidates: list[Candidate] = Field(default_factory=list)
    verdicts: list[Verdict] = Field(default_factory=list)
    impacts: dict[str, ImpactUnit] = Field(default_factory=dict)
    cards: list[Card] = Field(default_factory=list)
    allocation: AllocationSheet | None = None

    # instrumentation for the /runs/:id trace
    stage_timings: list[StageTiming] = Field(default_factory=list)
    tool_calls: int = 0

    def profile(self) -> OrgProfile:
        if self.org_profile is None:
            raise RuntimeError("FlowState.org_profile is not set before kickoff")
        return self.org_profile

    @property
    def cleared_verdicts(self) -> list[Verdict]:
        from app.flow.schemas import CauseStatus

        return [v for v in self.verdicts if v.status == CauseStatus.cleared]

    @property
    def has_development_need(self) -> bool:
        return any(
            v.candidate.need_type == NeedType.development for v in self.cleared_verdicts
        )
