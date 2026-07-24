"""Flow orchestration (spec §3).

A deterministic sequential executor threads the typed FlowState through every
stage. Routing is a plain conditional: score/compose only run when something
cleared; allocate always runs (an all-blocked quarter produces an empty sheet
with the whole budget visible as unallocated).

    scout    -> candidates
    verify   -> verdicts
    (cleared?) score -> impacts ; compose -> cards
    allocate -> allocation sheet

The agentic work is the you.com Research calls inside verify (multi-source web
verification) plus the OpenAI copy pass in compose; the decisions themselves
are code (spec §8: minimum code, no speculative abstraction). An earlier CrewAI
Flow wrapper was removed — it only re-called these same stage functions and
added a heavy dependency for no behavioural difference.
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


def run_pipeline(state: FlowState) -> FlowState:
    """Run all stages in order, recording per-stage timings on the state."""
    _timed(state, "scout", lambda: _do_scout(state))
    _timed(state, "verify", lambda: _do_verify(state))
    if state.cleared_verdicts:
        _timed(state, "score", lambda: _do_score(state))
        _timed(state, "compose", lambda: _do_compose(state))
    _timed(state, "allocate", lambda: _do_allocate(state))
    return state
