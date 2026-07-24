"""CrewAI Flow skeleton (spec §3).

Flows are the outer skeleton; the stage functions in this package are the
work. Deterministic routing and restartability come from the Flow; the typed
FlowState is threaded through every stage.

    @start   scout    -> candidates
    @listen  verify   -> verdicts
    @router  route    -> "cleared" | "blocked"
    @listen  score    -> impacts   (cleared only)
    @listen  compose  -> cards
    @listen  allocate -> allocation sheet

`run_pipeline_pure` runs the same stages sequentially without CrewAI so the
verify logic and the eval gate stay deterministic and testable offline. The
worker uses the CrewAI Flow; both call identical stage functions.
"""

from __future__ import annotations

import time

from app.flow import allocate, compose, score, scout, verify
from app.flow.state import FlowState, StageTiming


def _timed(state: FlowState, stage: str, fn: object) -> None:
    start = time.perf_counter()
    fn()  # type: ignore[operator]
    state.stage_timings.append(
        StageTiming(stage=stage, ms=round((time.perf_counter() - start) * 1000, 2))
    )


def _do_scout(state: FlowState) -> None:
    state.candidates = scout.run_scout(state).candidates


def _do_verify(state: FlowState) -> None:
    state.verdicts = verify.run_verify(state).verdicts


def _do_score(state: FlowState) -> None:
    state.impacts = score.run_score(state).impacts


def _do_compose(state: FlowState) -> None:
    state.cards = compose.run_compose(state).cards


def _do_allocate(state: FlowState) -> None:
    state.allocation = allocate.run_allocate(state)


def run_pipeline_pure(state: FlowState) -> FlowState:
    """Deterministic sequential executor — no CrewAI. Used by tests + eval gate."""
    _timed(state, "scout", lambda: _do_scout(state))
    _timed(state, "verify", lambda: _do_verify(state))
    if state.cleared_verdicts:
        _timed(state, "score", lambda: _do_score(state))
        _timed(state, "compose", lambda: _do_compose(state))
    _timed(state, "allocate", lambda: _do_allocate(state))
    return state


# --- CrewAI Flow ------------------------------------------------------------
# Imported lazily inside build_flow so tests that only exercise the pure path
# do not require crewai to be installed.

def build_flow(state: FlowState):  # type: ignore[no-untyped-def]
    from crewai.flow.flow import Flow, listen, or_, router, start

    class CauseFlow(Flow[FlowState]):  # type: ignore[type-arg]
        @start()
        def scout(self) -> str:
            _timed(self.state, "scout", lambda: _do_scout(self.state))
            return "scouted"

        @listen(scout)
        def verify(self) -> str:
            _timed(self.state, "verify", lambda: _do_verify(self.state))
            return "verified"

        @router(verify)
        def route(self) -> str:
            return "cleared" if self.state.cleared_verdicts else "blocked"

        @listen("cleared")
        def score(self) -> str:
            _timed(self.state, "score", lambda: _do_score(self.state))
            return "scored"

        @listen(score)
        def compose(self) -> str:
            _timed(self.state, "compose", lambda: _do_compose(self.state))
            return "composed"

        @listen(or_(compose, "blocked"))
        def allocate(self) -> str:
            # Both branches converge here: cleared causes produce lines, a
            # fully-blocked quarter produces an empty sheet with the whole
            # budget visible as unallocated.
            _timed(self.state, "allocate", lambda: _do_allocate(self.state))
            return "allocated"

    flow = CauseFlow()
    flow.state.run_id = state.run_id
    flow.state.org_profile = state.org_profile
    return flow


def execute_flow(state: FlowState) -> FlowState:
    """Run the CrewAI Flow; fall back to the pure executor on a CrewAI API
    mismatch so a version skew never silently drops a run. Both paths run the
    same stage functions and produce the same FlowState.
    """
    try:
        flow = build_flow(state)
        flow.kickoff()
        return flow.state  # type: ignore[return-value]
    except (ImportError, AttributeError, TypeError) as exc:  # pragma: no cover - env dependent
        import logging

        logging.getLogger(__name__).warning(
            "CrewAI Flow unavailable (%s); running pure executor", type(exc).__name__
        )
        return run_pipeline_pure(state)
