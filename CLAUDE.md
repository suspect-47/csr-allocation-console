# CLAUDE.md

**YourDues** — donor-facing **Social Cause Marketplace** built on an agentic cause
verification pipeline. A multi-step Python pipeline finds emerging charitable needs,
**independently verifies each one**, and only what clears (or a real, listed org) reaches
the storefront. Donors browse image-rich cause cards, pledge, earn Impact Points, follow
live events + news, **search the web live**, and **draft a fundable cause from any story
with AI**.

> Started as an internal **CSR allocation console** (still at `web/app/(site)`: `/`,
> allocation bar, dossiers); pivoted to the donor marketplace (`web/app/market/`) on the
> same pipeline. **Live: [yourdues-web.onrender.com/market](https://yourdues-web.onrender.com/market)**

Product thesis: **verification, not discovery.** Discovery is a search query; verification
is why this needs agents.

## Architecture — read before touching anything

Three parts. The web layer is Next.js; the verification pipeline is implemented and
tested in Python (verify logic, eval gate), so it runs as a separate Python worker.

| Part | Stack | Location | Job |
|------|-------|----------|-----|
| Marketplace | Next.js App Router (React, client) | `web/app/market/`, `web/lib/market.ts` | donor UI: causes, orgs, events, news, pledge, gamification |
| Operator console | Next.js App Router | `web/app/(site)/`, `web/lib/repo.ts` | internal: allocation bar, dossiers, runs |
| Web API | Next.js route handlers (Node/TS) | `web/app/api/`, `web/lib/` | read Postgres, enqueue, live news search + AI fund — **never runs the flow** |
| Agent engine | Python (deterministic pipeline + you.com/OpenAI) | `app/`, `scripts/gather_*` | runs the flow off the queue; gathers catalog/news/images |

Shared state: **Postgres** (`migrations/0001…0005`) + **Redis** queue key `csr:jobs`. Data
flow: `browser → Next /api (enqueue) → run row; worker BRPOP csr:jobs → pipeline (you.com
Research + OpenAI copy) → write Postgres; browser polls /api/runs/:id`. Marketplace reads
`/api/market`. The agentic work is the you.com Research calls in verify; decisions are
code. (An earlier CrewAI Flow wrapper was dropped — it only re-called the stage functions.)

## Layout

```text
app/                  Python agent engine
  flow/               scout → verify → route → score → compose → allocate (pipeline.py)
  clients/youcom.py   you.com Search + Research client (confirmed against live docs)
  worker.py cron.py   queue consumer / discovery enqueuer
  repository.py db.py kv.py   Postgres + Redis (Python side)
  eval/               deterministic eval gate + capture replay
web/                  Next.js (frontend + web API)
  app/(site)/         operator console pages
  app/market/         marketplace: page.tsx · news/ · causes/[id]/  (+ market.css)
  app/api/market/     market · news · news/search (live) · news/create-fund (AI)
  lib/                db.ts (pg) · kv.ts (ioredis) · market.ts · youcom.ts (node search) · ai.ts (OpenAI) · repo.ts · types.ts
  components/         Capybara.tsx (brand mark)
migrations/ 0001…0005   scripts/ (migrate, gather_catalog, gather_news, backfill_event_images, eval_gate, record_fixtures)
Dockerfile.web (Next standalone, binds 0.0.0.0:10000)   Dockerfile.worker (Python)   render.yaml
```

## Commands

```bash
# Python (agent engine) — the local stop-condition
make verify                      # ruff + mypy + pytest
python -m scripts.eval_gate      # red until real captures exist (by design)

# Next.js (frontend + web API)
cd web && npm run typecheck && npm run build
cd web && npm run dev            # UI + /api on :8000 (needs pg + kv)

# gather real marketplace data (you.com + OpenAI)
python -m scripts.gather_catalog          # orgs + causes + events + images
python -m scripts.gather_news             # articles + videos
python -m scripts.backfill_event_images   # event thumbnails

# full stack
docker compose up --build        # db + kv + migrate + web(Next) + worker → :8000
docker compose run --rm cron     # enqueue a discovery run
```

Git repo → GitHub `suspect-47/yourDues` (main). No `.venv` committed — recreate with
`pip install -r requirements.txt`. **Never commit `.env`** (public repo; gitignored).

## Deploy (Render)

Blueprint `render.yaml`: **web** (Docker) + **Postgres** + **Key Value**; **worker/cron**
are optional and **need a paid plan** (not required — data is seeded, search/AI run in web).
Secrets live in the `csr-secrets` env group (`sync:false`, set in dashboard). Web binds
`0.0.0.0:10000`; health check `/api/healthz`. Live services created via Render API.

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

- **you.com contract (confirmed live):** Search `GET https://ydc-index.io/v1/search` (query
  params, `X-API-Key`, response `results.web[]`/`results.news[]` with `thumbnail_url`/`favicon_url`);
  Research `POST https://api.you.com/v1/research`. Python client `app/clients/youcom.py`; Node-side
  live news search `web/lib/youcom.ts`. Base URLs env-configurable.
- **Web needs the API keys too.** `web/lib/youcom.ts` + `web/lib/ai.ts` read `YOU_SEARCH_API_KEY`,
  `OPENAI_API_KEY`, `CREW_MODEL` — the news search + AI-fund routes 500 without them (they're in
  the Render `csr-secrets` group).
- **Eval gate is red until real captures are recorded** (`scripts/record_fixtures.py`, needs keys).
  `tests/fixtures/records.json` = test specs; `captures/` = **real captures only**, empty by design.
- **Queue contract must stay in lockstep**: key `csr:jobs` + payload `{run_id, profile_id}` are
  duplicated in `app/kv.py` and `web/lib/kv.ts`. Change both together.
- **Postgres `numeric` returns as string in node-pg** — read queries in `web/lib/repo.ts` /
  `market.ts` cast money columns to `::float8`.
- **Pledge accepts `cleared` + `listed` causes** (`web/lib/market.ts`) — Fund must work on listed
  marketplace orgs, not only verified ones.
- **The worker applies migrations at startup** (Next/Node cannot run the Python migrate). On Render
  without the worker, run `scripts.migrate` against the DB manually.
- **Render gotchas:** free web hibernates when idle (cold start ~30–60 s); API-created Postgres
  defaults to an **empty IP allow-list** (open temporarily to seed, then re-lock).
- Keys are read from `os.environ` / `process.env` by name only — never log, print, or echo values.

## Non-goals (do not build — spec §0)

No payments/Stripe/checkout (allocation → pledge sheet only). No auth/signup. No admin/CMS/
settings. No email/notifications/webhooks-out. No multi-tenancy/RBAC. No mobile app. If a task
is not in the build order, say so rather than building it.
