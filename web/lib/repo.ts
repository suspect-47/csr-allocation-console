// Read/write queries (server only). Mirrors app/repository.py. Money columns are
// cast to float8 so node-pg returns numbers, not strings. The Python worker owns
// writing causes/evidence; this layer creates profiles, runs, and committed
// allocations, and reads everything the UI needs.

import { randomUUID } from "crypto";
import { one, q } from "./db";
import type { CauseDetail, ConsoleCard, LedgerItem, Profile, Run } from "./types";

export async function activeProfiles(): Promise<Profile[]> {
  return q<Profile>(
    `select id, name, pillars, geographies, quarterly_budget::float8 as quarterly_budget, currency
     from org_profiles order by created_at`
  );
}

export async function createProfile(p: Omit<Profile, "id">): Promise<string> {
  const row = await one<{ id: string }>(
    `insert into org_profiles (name, pillars, geographies, quarterly_budget, currency)
     values ($1, $2, $3, $4, $5) returning id`,
    [p.name, p.pillars, p.geographies, p.quarterly_budget, p.currency]
  );
  return row!.id;
}

export async function createRun(): Promise<string> {
  const id = randomUUID();
  await q(`insert into runs (id, status, started_at) values ($1, 'queued', now())`, [id]);
  return id;
}

export async function clearedCards(): Promise<ConsoleCard[]> {
  return q<ConsoleCard>(
    `select c.id, c.org_name, c.org_domain, c.headline, c.summary, c.geography,
            c.pillar, c.need_type,
            exists(select 1 from evidence e
                   where e.cause_id = c.id and e.result = 'unknown') as has_unknown,
            (select a.amount::float8 from allocations a
             where a.cause_id = c.id order by a.created_at desc limit 1) as amount
     from causes c
     where c.status = 'cleared'
     order by c.created_at desc`
  );
}

export async function blockedCauses(): Promise<LedgerItem[]> {
  return q<LedgerItem>(
    `select id, org_name, headline, summary, geography, pillar, need_type, blocking_check
     from causes where status = 'blocked' order by created_at desc`
  );
}

export async function causeDetail(id: string): Promise<CauseDetail | null> {
  const cause = await one<CauseDetail["cause"]>(`select * from causes where id = $1`, [id]);
  if (!cause) return null;
  const evidence = await q<CauseDetail["evidence"][number]>(
    `select check_name, result, source_url, source_title, excerpt, retrieved_at
     from evidence where cause_id = $1 order by check_name`,
    [id]
  );
  const impact = await one<NonNullable<CauseDetail["impact"]>>(
    `select unit_label, unit_cost::float8 as unit_cost, currency, is_stated, stated_by_url
     from impact_units where cause_id = $1`,
    [id]
  );
  return { cause, evidence, impact };
}

export async function listRuns(limit = 25): Promise<Run[]> {
  return q<Run>(
    `select id, status, started_at, finished_at, found, cleared, blocked, tool_calls
     from runs order by started_at desc limit $1`,
    [limit]
  );
}

export async function getRun(id: string): Promise<Run | null> {
  return one<Run>(`select * from runs where id = $1`, [id]);
}

export async function insertCommittedAllocations(
  profileId: string,
  lines: { cause_id: string; amount: number; rationale: string }[]
): Promise<void> {
  for (const l of lines) {
    await q(
      `insert into allocations (org_profile_id, cause_id, amount, rationale, created_at)
       values ($1, $2, $3, $4, now())`,
      [profileId, l.cause_id, l.amount, l.rationale]
    );
  }
}
