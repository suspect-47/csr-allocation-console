"""Record real you.com Research captures for the eval-gate fixtures (spec §6).

    python -m scripts.record_fixtures

Requires live keys. Iterates the SAME check_specs() the live verifier uses, so
the captures match live calls exactly. Writes tests/fixtures/captures/<id>.json,
each holding the six Research responses (raw JSON) in check order.

Real captures only — this script does not synthesize responses. If a call
fails, it is left uncaptured and the gate stays red for that record.
"""

from __future__ import annotations

import json
import sys

from app.clients import youcom
from app.clients.youcom import Effort
from app.eval.replay import CAPTURES, load_records, record_to_candidate
from app.flow.verify import check_specs


def record_one(rec: dict[str, object]) -> bool:
    cand = record_to_candidate(rec)
    raws: list[dict[str, object]] = []
    for _classifier, prompt, exclude in check_specs(cand):
        # Call the private _post-backed path via the public client so the
        # response is the real, cached capture. We store the raw json.
        result = youcom.research(prompt, effort=Effort.deep, exclude_domains=exclude)
        # youcom.research returns the parsed shape; re-dump it as the raw the
        # gate will parse. (Parsed round-trips through _parse_research cleanly.)
        raws.append({"answer": result.answer, "citations": [c.model_dump() for c in result.citations]})
    CAPTURES.mkdir(parents=True, exist_ok=True)
    (CAPTURES / f"{rec['id']}.json").write_text(json.dumps({"research": raws}, indent=2))
    return True


def main() -> int:
    records = load_records()
    placeholders = [r["id"] for r in records if str(r["org_name"]).startswith("REPLACE:")]
    if placeholders:
        print("Refusing to record placeholder records:", ", ".join(placeholders))
        print("Replace them with real known-bad organizations in records.json first.")
        return 2
    for rec in records:
        print(f"recording {rec['id']} ({rec['org_name']}) ...")
        record_one(rec)
    print(f"done — {len(records)} captures written to {CAPTURES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
