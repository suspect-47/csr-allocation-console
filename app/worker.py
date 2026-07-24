"""Worker — CrewAI flow executor (spec §1).

Pulls one job from the Key Value queue, runs exactly one flow to completion,
persists causes + evidence + allocation, updates the run row. Sequential: one
flow run per job. A crew never runs inside an HTTP handler — only here.
"""

from __future__ import annotations

import logging
import signal
import sys
from types import FrameType
from typing import Any

from app import kv, repository
from app.flow.pipeline import execute_flow
from app.flow.state import FlowState

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("worker")

_running = True


def _stop(_sig: int, _frame: FrameType | None) -> None:
    global _running
    log.info("shutdown signal received; finishing current job then exiting")
    _running = False


def process_job(job: dict[str, Any]) -> None:
    run_id = job["run_id"]
    profile_id = job["profile_id"]
    log.info("run %s: starting (profile %s)", run_id, profile_id)

    profile = repository.get_profile(profile_id)
    if profile is None:
        repository.set_run_status(run_id, "failed")
        log.error("run %s: profile %s not found", run_id, profile_id)
        return

    repository.set_run_status(run_id, "running")
    state = FlowState(run_id=run_id, org_profile=profile)
    try:
        state = execute_flow(state)
        repository.persist_results(run_id, state)
        repository.finish_run(run_id, state, "succeeded")
        log.info(
            "run %s: done found=%d cleared=%d tool_calls=%d",
            run_id, len(state.candidates), len(state.cleared_verdicts), state.tool_calls,
        )
    except Exception:  # noqa: BLE001 - a run failure must mark the row, not crash the worker
        log.exception("run %s: failed", run_id)
        repository.finish_run(run_id, state, "failed")


def main() -> int:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    # The web service is Next.js (Node) and cannot run the Python migrations,
    # so the worker applies them at startup. migrate.run() is idempotent.
    from scripts.migrate import run as run_migrations

    run_migrations()
    log.info("worker up; polling %s", kv.QUEUE_KEY)
    while _running:
        job = kv.dequeue_job(timeout_seconds=5)
        if job is None:
            continue
        process_job(job)
    return 0


if __name__ == "__main__":
    sys.exit(main())
