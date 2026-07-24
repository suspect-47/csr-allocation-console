# CSR Allocation Console

A corporate-giving lead sets pillars, geography, and a quarterly budget. A
multi-agent system continuously finds emerging charitable needs on the open web,
**independently verifies each one**, publishes only what clears, and proposes a
budget allocation with a sourced rationale.

The product thesis is **verification, not discovery**. Discovery is a search
query; verification is why this needs agents. Nothing in this system estimates,
infers, or fills in a number a source did not state — that rule outranks
completeness everywhere it conflicts.

---

## Stack

| Concern | Tool |
|---|---|
| Orchestration | Deterministic Python pipeline (CrewAI dropped — see note) |
| Web retrieval / verification | you.com Search API (discovery) + Research API (verification) |
| Reasoning model | OpenAI (`gpt-4o-mini`) via litellm — polishes card copy only (deviation from spec's Claude, per user) |
| Runtime | Render — web + worker + cron + Postgres + Key Value |
| CI / gate / deploy trigger | Opsera |
| Frontend + web API | **Next.js (App Router)** — React UI + `/api` route handlers |
| Agent flow | **Python worker + cron** — sequential pipeline |

> **CrewAI was dropped.** It only wrapped the deterministic stage functions in a
> `Flow` skeleton and added a heavy dependency (plus a litellm pin conflict) for
> no behavioural difference — the pure executor already produced identical runs.
> The genuine "agents" are the you.com Research calls (multi-source verification)
> and the OpenAI copy pass; decisions are code (spec §8). Deviates from spec §1.

### Architecture: Next.js front + back, Python pipeline

`web/` is a **Next.js** app: it renders the React UI **and** serves the `/api/*`
route handlers (reads Postgres, enqueues jobs). The **Python worker** runs the
verification pipeline; **cron** enqueues discovery. Web and worker share one
Postgres and one Redis queue (`csr:jobs`) — "web enqueues, worker executes". The
pipeline stays Python because that is where the verify logic and tests live.

### The one boundary that matters

**Opsera owns the gate. Render owns the runtime.** Every Render service has
`autoDeploy: false`; deploys happen **only** via the Render deploy hook, called
as the final Opsera stage. Do not enable Opsera VIBEshift for steady-state
deploys — it provisions its own infra and duplicates the Render services.

The flow never runs inside an HTTP request. **Web (Next.js) enqueues, worker
executes, UI polls** `/api/runs/{id}`.

---

## Local development

```bash
cp .env.example .env          # fill keys when you have them; blanks are fine to boot
docker compose up --build     # db + kv + migrate (one-shot) + web (Next) + worker
# open http://localhost:8000  → lands on /profile on a clean install
docker compose run --rm cron  # enqueue a discovery run (or click "Run discovery")
```

Frontend + API hot reload (needs db + kv + worker running; worker applies
migrations at startup):

```bash
cd web && npm install && npm run dev   # http://localhost:8000 (UI + /api)
```

### Verify (the local stop-condition, mirrors the Opsera gate minus deploy)

```bash
make verify                       # ruff + mypy + pytest (Python)
cd web && npm run typecheck && npm run build   # Next.js (tsc strict + build)
```

---

## ⚠️ Build status — read this

This repo was built **offline, without live credentials** (a deliberate choice —
see below). Two things follow, both intentional and documented in-code:

1. **you.com client is flagged `VERIFY`.** Spec §2 says derive the client from
   the live docs; doc access was unavailable at build time. `app/clients/youcom.py`
   has env-configurable base URLs / auth header and a tolerant response parser,
   wrapped in a `VERIFY against live docs` banner. Confirm these before the first
   live call:
   - `docs.you.com/api-reference/search/v1-search`
   - `you.com/docs/api-reference/research/v1-research`
   - adjust `YOU_SEARCH_BASE_URL` / `YOU_RESEARCH_BASE_URL` in `.env`, and
     `AUTH_HEADER` / the field names in `_parse_search` / `_parse_research`.

2. **The eval gate is red until you record real captures.** Fixtures follow the
   no-fake rule: `tests/fixtures/records.json` holds test specs; the real API
   captures in `tests/fixtures/captures/` do **not** exist yet, so
   `python -m scripts.eval_gate` exits non-zero by design. See
   `tests/fixtures/README.md`.

3. **Pinned versions are intentional** (`requirements.txt`) — confirm exact
   patch versions against your index.

The offline-buildable code (schemas, verify logic, allocation constraints,
cache, scout dedupe, API, SPA) is covered by `pytest` and can be run with
`make verify`. The credentialed paths (steps 2, 4, 5 in §9) need keys.

---

## Bringing it live

1. Put keys in `.env`: `YOU_SEARCH_API_KEY`, `YOU_RESEARCH_API_KEY`,
   `OPENAI_API_KEY`. Code references names only — never logs values.
2. Confirm the you.com client `VERIFY` items above.
3. Record fixtures (needs keys; replace the four `bad-*` placeholders with real
   known-bad orgs first):
   ```bash
   python -m scripts.record_fixtures
   python -m scripts.eval_gate      # now green
   ```

---

## First-run path (spec §10 — nothing is pre-inserted)

Empty database → `/profile` setup → **Run discovery** → worker runs the flow →
console fills from an empty database with zero manual row insertion.

```
/           allocation console — budget bar, cleared cards, commit → pledge sheet
/causes/:id dossier — full evidence chain, all six checks, every source link
/ledger     did not clear — blocked causes with the failing check named
/runs/:id   run trace — flow stages, timings, tool-call counts, live status
/profile    pillar / geography / budget setup (clean install lands here)
```

The signature element is the **allocation bar**: drag a segment edge to
rebalance, the adjacent segment compensates, the unallocated remainder stays a
visible hatched region. Verification state is encoded as **texture + color**
(solid = cleared, diagonal hatch = a check returned unknown) — never color alone.

---

## The flow (`app/flow/`)

```
scout    → candidates   (Search; proposes, never judges)
verify   → verdicts     (Research ×6 per candidate; the core)
route    → cleared / blocked   (plain conditional)
score    → impacts      (stated unit cost only, else null)
compose  → cards        (every claim cited + optional OpenAI polish)
allocate → sheet        (≤40% cap, ≥20% development, remainder visible)
```

Verdict rule, impact fabrication guard, citation coverage, and allocation
constraints are enforced **in code** (Pydantic validators + `decide_verdict`),
never left to the model — the eval gate replays real captures and fails the
build if any known-bad clears, if a legit fixture is over-blocked, if citation
coverage drops below 100%, or if the fabrication guard is removed.

---

## Non-goals (not built, by design — spec §0)

No payments/Stripe/checkout (allocation → pledge sheet only). No auth/signup. No
seeded/mock/sample cause data — every cause carries an evidence chain. No admin
panel, CMS, settings page, email, notifications, webhooks-out, multi-tenancy,
RBAC, or audit log beyond the evidence tables. No mobile app — responsive web.
