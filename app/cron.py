"""Cron — ingestion trigger (spec §1, runs every 30 min).

Enqueues one discovery job per active org profile, then exits. Creating the run
row here (not in the worker) means the UI can poll a run the instant it is
queued. This script does no crew work.
"""

from __future__ import annotations

import logging

from app import kv, repository

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cron")


def enqueue_discovery() -> int:
    profiles = repository.active_profiles()
    if not profiles:
        log.info("no active org profiles; nothing to enqueue")
        return 0
    for profile in profiles:
        assert profile.id is not None
        run_id = repository.create_run()
        kv.enqueue_job({"run_id": run_id, "profile_id": profile.id})
        log.info("enqueued run %s for profile %s (%s)", run_id, profile.id, profile.name)
    return len(profiles)


if __name__ == "__main__":
    enqueue_discovery()
