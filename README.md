# YourDues — Social Cause Marketplace

**Live: [yourdues-web.onrender.com/market](https://yourdues-web.onrender.com/market)**

A donor-facing marketplace of charitable causes where **every cause carries an
evidence chain**. A multi-step pipeline finds emerging needs on the open web,
**independently verifies each one** (you.com Research, ×6 checks), and only what
clears — or is a real, listed org — reaches the storefront. Donors browse
image-rich cause cards, pledge, earn Impact Points, and follow live events and
news; they can also **search the web live** and **draft a fundable cause from any
story with AI**.

Product thesis: **verification, not discovery.** Discovery is a search query;
verification is why this needs agents. Nothing here estimates, infers, or fills
in a number a source did not state — that rule outranks completeness.

> Started as an internal **CSR allocation console**; pivoted to a donor-facing
> marketplace on top of the same verification pipeline. The operator console
> (`/`, allocation bar, dossiers) still ships under `web/app/(site)`.

---

## Stack

| Concern | Tool |
|---|---|
| Frontend + web API | **Next.js (App Router)** — React UI + `/api/*` route handlers |
| Cause verification | **Python** deterministic pipeline (`app/flow/`) |
| Web retrieval | **you.com** — Search (discovery, live news, org/image gathering) + Research (×6 verification) |
| Reasoning model | **OpenAI** `gpt-4o-mini` via litellm — card copy + "draft a fund from news" |
| Shared state | **Postgres** (6+ tables) + **Redis** queue (`csr:jobs`) |
| Runtime | **Render** — web + Postgres + Key Value (worker + cron optional, paid) |
| Fonts / look | Lexend + Pacifico wordmark; light-emerald liquid-glass bento UI |

### Architecture — two apps, one database

`web/` is a **Next.js** app: renders the marketplace UI **and** serves `/api/*`
(reads Postgres, enqueues jobs, live you.com news search, OpenAI fund drafting).
The **Python worker** runs the verification pipeline off the `csr:jobs` queue;
**cron** enqueues discovery. Web enqueues, worker executes — the flow never runs
inside an HTTP request. The pipeline stays Python because that is where the
verify logic and tests live.

```text
browser → Next /api (enqueue) → run row
worker BRPOP csr:jobs → pipeline (you.com Research + OpenAI) → write Postgres
browser polls /api/runs/:id   ·   marketplace reads /api/market
```

---

## What's in the marketplace

- **Causes** — verified + listed orgs as bento cards with real images/logos,
  rarity (verification strength), momentum, backers, pillar filter + sort.
- **Trending orgs** — real orgs (you.com), transparent logos.
- **Live events** — real events with thumbnails backfilled per event.
- **News & stories** — gathered articles + videos, **live web search** on demand,
  and **✨ Create fund** — OpenAI drafts a fundable cause from any story.
- **Gamification** — Impact Points, level, streak + daily quests, leaderboard.
- **Pledge** — records a pledge, awards points (allocation → pledge, no checkout).

Routes: `/market`, `/market/news`, `/market/causes/:id`. Operator console lives
at `/`, `/causes/:id`, `/ledger`, `/runs/:id`, `/profile`.

---

## Local development (native)

```bash
# infra
brew services start postgresql@16 redis      # or docker compose up db kv
createdb causes                               # DATABASE_URL=postgresql://.../causes

# secrets — names only, never logged. NEVER commit .env (public repo).
cp .env.example .env    # YOU_SEARCH_API_KEY, YOU_RESEARCH_API_KEY, OPENAI_API_KEY, DATABASE_URL, KV_URL

# python engine
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python -m scripts.migrate                     # apply migrations/000*.sql

# gather real marketplace data (you.com + OpenAI)
python -m scripts.gather_catalog              # orgs + cleared/listed causes + events + images
python -m scripts.gather_news                 # articles + videos
python -m scripts.backfill_event_images       # event thumbnails

# web (UI + /api) on :8000
cd web && npm install && npm run dev
```

Full stack in Docker: `docker compose up --build` (db + kv + migrate + web +
worker). Enqueue a run: `docker compose run --rm cron`.

### Verify (local stop-condition)

```bash
make verify                                    # ruff + mypy + pytest (Python)
cd web && npm run typecheck && npm run build   # Next.js (tsc strict + build)
```

---

## Deploy on Render

Blueprint in [`render.yaml`](render.yaml): **web** (Docker, `Dockerfile.web`) +
**Postgres** + **Key Value**, plus optional **worker**/**cron** (paid). Secrets
live in the `csr-secrets` env group (`sync:false` — set values in the dashboard).

1. **New → Blueprint** → connect the repo → apply. Enter the 3 secret keys.
2. Migrations run at worker startup (or `python -m scripts.migrate` against the DB).
3. Seed the DB with gathered data, then open the web URL → `/market`.

Notes:

- Web binds `0.0.0.0:10000` (`Dockerfile.web`) so Render's router reaches Next
  standalone; health check is `/api/healthz`.
- Free web hibernates when idle → first request cold-starts (~30–60 s).
- Render API-created Postgres defaults to an **empty IP allow-list** (no external
  access) — open it temporarily only to seed, then re-lock.

---

## Hard rules (enforced in code, not prompts)

- **No fabricated numbers.** Impact cost is null unless a source stated it
  (`ImpactUnit.is_stated`; Pydantic validator + Postgres CHECK). Never divide
  budget by beneficiaries.
- **No seed/mock/sample cause data.** Every cause arrives through the pipeline
  or `gather_*` with an evidence row. A cause with no evidence is a bug.
- **Decisions in code.** Verdict rule (`decide_verdict`), allocation constraints
  (≤40% cap, ≥20% development, visible remainder), citation coverage — code +
  validators. The you.com Research calls are the "agentic" work.
- **A check with no source URL is `unknown`, never `pass`.**

## The flow (`app/flow/`)

```text
scout    → candidates   (Search; proposes, never judges)
verify   → verdicts     (Research ×6 per candidate; the core)
route    → cleared / blocked
score    → impacts      (stated unit cost only, else null)
compose  → cards        (every claim cited + optional OpenAI polish)
allocate → sheet        (≤40% cap, ≥20% development, remainder visible)
```

## Non-goals (not built, by design)

No payments/Stripe/checkout (pledge sheet only). No auth/signup. No admin/CMS/
settings, email, notifications, webhooks-out, multi-tenancy, RBAC. No mobile app
— responsive web.
