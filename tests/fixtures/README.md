# Eval-gate fixtures (spec §6)

Two kinds of file live here. Keep them straight:

| File | What it is | Hand-written? |
|------|------------|---------------|
| `records.json` | Test inputs + expected verdicts (10 records: 6 legit, 4 bad) | Yes — it's a test spec |
| `captures/<id>.json` | The real you.com Research responses for each record, in check order | **No — real captures only** |

The captures are **real API captures, never hand-written** (spec §6). They do
not exist in the repo yet, so the eval gate is **red by design** until you
record them. That is the correct state, not a bug.

## Recording

1. Put live keys in `.env` (`YOU_RESEARCH_API_KEY`, and confirm the base URL /
   auth header in `app/clients/youcom.py` against the live docs first).
2. Replace the four `bad-*` placeholders in `records.json` with real
   known-bad organizations (defunct, unregistered, or with a documented
   complaint). Do not label a legitimate org as bad.
3. Run the recorder:

   ```bash
   python -m scripts.record_fixtures
   ```

   It iterates the same `check_specs()` the live verifier uses, so captures
   match live calls exactly. One `captures/<id>.json` per record, each holding
   the six Research responses in check order.

4. Run the gate:

   ```bash
   python -m scripts.eval_gate
   ```

These captures are test infrastructure only. They are **never** loaded into the
application database — the no-seed rule (spec §0) still holds.
