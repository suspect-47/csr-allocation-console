-- Marketplace / gamification layer. Causes, evidence, impact stay the source of
-- truth (verified pipeline data). These tables hold app-generated state — real
-- pledges and patron progress — not fabricated social proof. Backers start at 0
-- and grow as people actually fund.

create table if not exists patrons (
    id            uuid primary key default gen_random_uuid(),
    name          text        not null,
    impact_points integer      not null default 0,
    streak_days   integer      not null default 0,
    last_pledge_at timestamptz,
    created_at    timestamptz not null default now()
);

create table if not exists pledges (
    id         uuid primary key default gen_random_uuid(),
    cause_id   uuid        not null references causes (id) on delete cascade,
    patron_id  uuid        not null references patrons (id) on delete cascade,
    amount     numeric      not null check (amount > 0),
    created_at timestamptz not null default now()
);
create index if not exists pledges_cause_idx on pledges (cause_id);

create table if not exists events (
    id           uuid primary key default gen_random_uuid(),
    title        text        not null,
    pillar       text,
    geography    text,
    status       text        not null default 'live',   -- live | soon | ended
    source_url   text,
    source_title text,
    starts_at    text,
    created_at   timestamptz not null default now()
);

-- Default demo patron ("You"). This is user/app state, not cause data — the
-- no-seed rule (spec §0) is about seeded causes, which never happens here.
insert into patrons (name, impact_points, streak_days)
select 'You', 0, 0
where not exists (select 1 from patrons);
