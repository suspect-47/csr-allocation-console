# CLAUDE.md

CSR allocation console with agentic cause verification. A corporate-giving lead sets
pillars, geography, and a quarterly budget; a multi-agent pipeline finds emerging
charitable needs, **independently verifies each one**, publishes only what clears, and
proposes a sourced budget allocation.

Product thesis: **verification, not discovery.** Discovery is a search query; verification
is why this needs agents.

## Architecture — read before touching anything

Three parts. The web layer is Next.js; the verification pipeline is implemented and
tested in Python (verify logic, eval gate), so it runs as a separate Python worker.

| Part | Stack | Location | Job |
|------|-------|----------|-----|
| Frontend | Next.js App Router (React, client components) | `web/app/*/page.tsx`, `web/components/` | UI |
| Web API | Next.js route handlers (Node/TS) | `web/app/api/`, `web/lib/` | read Postgres, enqueue jobs — **never runs the flow** |
| Agent engine | Python (deterministic pipeline + you.com/OpenAI) | `app/` | runs the flow off the queue |

Shared state: **Postgres** (6 tables, `migrations/0001_init.sql`) + **Redis** queue key
`csr:jobs`. Data flow: `browser → Next /api (enqueue) → run row; worker BRPOP csr:jobs →
pipeline (you.com Research + OpenAI copy) → write Postgres; browser polls /api/runs/:id`.
The agentic work is the you.com Research calls in verify; decisions are code. (An earlier
CrewAI Flow wrapper was dropped — it only re-called the same stage functions.)

## Layout

```
app/                  Python agent engine
  flow/               scout → verify → route → score → compose → allocate (pipeline.py)
  clients/youcom.py   you.com Search + Research client (VERIFY-flagged, see below)
  worker.py cron.py   queue consumer / discovery enqueuer
  repository.py db.py kv.py   Postgres + Redis (Python side)
  eval/               deterministic eval gate + capture replay
web/                  Next.js (frontend + web API)
  app/api/*/route.ts  8 endpoints
  lib/                db.ts (pg) · kv.ts (ioredis) · repo.ts · allocation.ts · types.ts · api.ts (client)
migrations/  scripts/ (migrate, eval_gate, record_fixtures)  tests/  .opsera/pipeline.yml
Dockerfile.web (Next standalone)   Dockerfile.worker (Python)   render.yaml
```

## Commands

```bash
# Python (agent engine) — the local stop-condition
make verify                      # ruff + mypy + pytest
python -m scripts.eval_gate      # red until real captures exist (by design)

# Next.js (frontend + web API)
cd web && npm run typecheck && npm run build

# full stack
docker compose up --build        # db + kv + migrate + web(Next) + worker → :8000
docker compose run --rm cron     # enqueue a discovery run
```

No git repo (intentional). No `.venv` committed — recreate with `pip install -r requirements.txt`.

## Hard rules — never break these

- **No fabricated numbers.** Impact cost is null unless a source stated it (`ImpactUnit.is_stated`).
  Never divide budget by beneficiaries. Enforced by Pydantic validator + a Postgres CHECK.
- **No seed/mock/sample cause data.** Every cause arrives through the pipeline with an evidence
  chain. A cause with no evidence rows is a bug.
- **Decisions in code, not the model.** The verdict rule (`decide_verdict`), allocation
  constraints (≤40% cap, ≥20% development, visible remainder), and citation coverage are code +
  validators, not prompt instructions. The you.com Research calls are the "agentic" work.
- **Web never runs the flow.** HTTP handlers enqueue; the worker executes. The flow in a request
  handler times out.
- **A check with no source URL is `unknown`, never `pass`.**

## Gotchas

- **you.com client is `VERIFY`-flagged** (`app/clients/youcom.py`) — base URLs / auth header /
  response fields were not confirmable at build time. Confirm against live docs before the first
  live call; they are env-configurable.
- **Eval gate is red until real captures are recorded** (`scripts/record_fixtures.py`, needs
  keys). `tests/fixtures/records.json` = test specs (fine to hand-write); `captures/` = **real
  captures only**, empty by design.
- **Queue contract must stay in lockstep**: key `csr:jobs` + payload `{run_id, profile_id}` are
  duplicated in `app/kv.py` and `web/lib/kv.ts`. Change both together.
- **Postgres `numeric` returns as string in node-pg** — read queries in `web/lib/repo.ts` cast
  money columns to `::float8`.
- **The worker applies migrations at startup** (Next/Node cannot run the Python migrate).
- Keys are read from `os.environ` by name only — never log, print, or echo values.

## Non-goals (do not build — spec §0)

No payments/Stripe/checkout (allocation → pledge sheet only). No auth/signup. No admin/CMS/
settings. No email/notifications/webhooks-out. No multi-tenancy/RBAC. No mobile app. If a task
is not in the build order, say so rather than building it.
