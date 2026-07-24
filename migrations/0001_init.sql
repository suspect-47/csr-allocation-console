-- Schema for the CSR allocation console (spec §4).
-- Every cause carries an evidence chain. A cause with no evidence is a bug;
-- there is no seed data — every row arrives through the pipeline.

create extension if not exists pgcrypto;

create table if not exists org_profiles (
    id               uuid primary key default gen_random_uuid(),
    name             text        not null,
    pillars          text[]      not null,
    geographies      text[]      not null,
    quarterly_budget numeric      not null check (quarterly_budget > 0),
    currency         text        not null default 'USD',
    created_at       timestamptz not null default now()
);

create table if not exists causes (
    id             uuid primary key default gen_random_uuid(),
    org_name       text        not null,
    org_domain     text,
    headline       text        not null,
    summary        text        not null,
    geography      text        not null,
    pillar         text        not null,
    need_type      text        not null check (need_type in ('acute', 'development')),
    status         text        not null check (status in ('cleared', 'blocked')),
    blocking_check text,
    created_at     timestamptz not null default now()
);
create index if not exists causes_status_idx on causes (status, created_at desc);

create table if not exists evidence (
    id           uuid primary key default gen_random_uuid(),
    cause_id     uuid        not null references causes (id) on delete cascade,
    check_name   text        not null,
    result       text        not null check (result in ('pass', 'fail', 'unknown')),
    source_url   text,
    source_title text,
    excerpt      text        check (char_length(excerpt) <= 200),  -- store the link, not the article
    retrieved_at timestamptz not null default now()
);
create index if not exists evidence_cause_idx on evidence (cause_id);

create table if not exists impact_units (
    cause_id      uuid primary key references causes (id) on delete cascade,
    unit_label    text,
    unit_cost     numeric,
    currency      text,
    is_stated     boolean not null default false,
    stated_by_url text,
    -- Database-level guard for the product's worst failure mode: a non-null
    -- cost must be source-stated (spec §3.3). Mirrors the Pydantic validator.
    constraint impact_no_fabrication check (not (unit_cost is not null and is_stated = false))
);

create table if not exists allocations (
    id             uuid primary key default gen_random_uuid(),
    org_profile_id uuid        references org_profiles (id) on delete set null,
    cause_id       uuid        not null references causes (id) on delete cascade,
    amount         numeric      not null check (amount >= 0),
    rationale      text        not null,
    created_at     timestamptz not null default now()
);
create index if not exists allocations_cause_idx on allocations (cause_id, created_at desc);

create table if not exists runs (
    id            uuid primary key,
    status        text        not null,
    started_at    timestamptz not null default now(),
    finished_at   timestamptz,
    stage_timings jsonb,
    found         integer,
    cleared       integer,
    blocked       integer,
    tool_calls    integer
);
create index if not exists runs_started_idx on runs (started_at desc);
