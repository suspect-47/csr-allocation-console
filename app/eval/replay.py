"""Load eval-gate records and replay recorded you.com responses (spec §6).

The gate must be deterministic — it replays real captures rather than hitting
the network. Captures are stored per record in check order and parsed through
the same `_parse_research` the live client uses, so replay and live are identical.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from app.clients import youcom
from app.clients.youcom import ResearchResult, _parse_research
from app.flow.schemas import Candidate, NeedType

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
RECORDS = FIXTURES / "records.json"
CAPTURES = FIXTURES / "captures"


def load_records() -> list[dict[str, Any]]:
    return cast("list[dict[str, Any]]", json.loads(RECORDS.read_text())["records"])


def record_to_candidate(rec: dict[str, Any]) -> Candidate:
    domain = rec.get("org_domain")
    source_url = f"https://{domain}" if domain else f"https://placeholder.invalid/{rec['id']}"
    return Candidate(
        org_name=rec["org_name"],
        org_domain=domain,
        claim=rec["claim"],
        source_url=source_url,
        source_title=rec["org_name"],
        need_type=NeedType(rec["need_type"]),
        pillar=rec["pillar"],
        geography=rec["geography"],
    )


def captures_path(record_id: str) -> Path:
    return CAPTURES / f"{record_id}.json"


def captures_available() -> bool:
    return all(captures_path(r["id"]).exists() for r in load_records())


def load_captures(record_id: str) -> list[ResearchResult]:
    raws = json.loads(captures_path(record_id).read_text())["research"]
    return [_parse_research(raw) for raw in raws]


@contextmanager
def replay_research(captures: list[ResearchResult]) -> Iterator[None]:
    """Patch youcom.research to return captured responses in call order."""
    original = youcom.research
    index = {"i": 0}

    def _fake(prompt: str, **_kwargs: object) -> ResearchResult:
        i = index["i"]
        if i >= len(captures):
            raise AssertionError("more research calls than recorded captures")
        index["i"] = i + 1
        return captures[i]

    youcom.research = _fake
    try:
        yield
    finally:
        youcom.research = original
