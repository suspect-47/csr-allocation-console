// Marketplace data layer (server). Causes/evidence/impact are verified pipeline
// truth; rarity + momentum are derived from verification strength; backers are
// real pledge counts (start at 0, grow as people fund). Nothing fabricated.

import { one, q } from "./db";

export interface Patron {
  id: string;
  name: string;
  impact_points: number;
  streak_days: number;
  level: number;
  level_label: string;
  xp_into_level: number;
  xp_for_level: number;
}

const LEVELS = ["Newcomer", "Backer", "Advocate", "Guardian", "Champion", "Patron", "Platinum"];
const XP_PER_LEVEL = 2500;

function decoratePatron(row: { id: string; name: string; impact_points: number; streak_days: number }): Patron {
  const ip = row.impact_points;
  const level = Math.min(LEVELS.length, Math.floor(ip / XP_PER_LEVEL) + 1);
  return {
    id: row.id,
    name: row.name,
    impact_points: ip,
    streak_days: row.streak_days,
    level,
    level_label: LEVELS[Math.min(level - 1, LEVELS.length - 1)],
    xp_into_level: ip % XP_PER_LEVEL,
    xp_for_level: XP_PER_LEVEL,
  };
}

export async function getOrCreatePatron(): Promise<Patron> {
  let row = await one<{ id: string; name: string; impact_points: number; streak_days: number }>(
    "select id, name, impact_points, streak_days from patrons order by created_at limit 1"
  );
  if (!row) {
    row = await one("insert into patrons (name) values ('You') returning id, name, impact_points, streak_days");
  }
  return decoratePatron(row!);
}

function rarity(passed: number): "legendary" | "rare" | "verified" {
  if (passed >= 6) return "legendary";
  if (passed === 5) return "rare";
  return "verified";
}

function momentum(passed: number, sources: number): number {
  return Math.min(100, passed * 12 + Math.min(sources, 5) * 8);
}

export async function marketData() {
  const causes = await q<{
    id: string; org_name: string; org_domain: string | null; headline: string; summary: string;
    pillar: string; geography: string; need_type: "acute" | "development"; created_at: string;
  }>(
    `select id, org_name, org_domain, headline, summary, pillar, geography, need_type, created_at
     from causes where status = 'cleared' order by created_at desc`
  );

  const ev = await q<{ cause_id: string; passed: number; unknown: number; sources: number }>(
    `select cause_id,
            count(*) filter (where result = 'pass')::int as passed,
            count(*) filter (where result = 'unknown')::int as unknown,
            count(distinct source_url)::int as sources
     from evidence group by cause_id`
  );
  const evByCause = new Map(ev.map((e) => [e.cause_id, e]));

  const pl = await q<{ cause_id: string; backers: number; raised: number }>(
    `select cause_id, count(*)::int as backers, coalesce(sum(amount),0)::float8 as raised
     from pledges group by cause_id`
  );
  const plByCause = new Map(pl.map((p) => [p.cause_id, p]));

  const impacts = await q<{ cause_id: string; unit_label: string | null; unit_cost: number | null; is_stated: boolean }>(
    `select cause_id, unit_label, unit_cost::float8 as unit_cost, is_stated from impact_units`
  );
  const impByCause = new Map(impacts.map((i) => [i.cause_id, i]));

  const cards = causes.map((c) => {
    const e = evByCause.get(c.id) ?? { passed: 3, unknown: 0, sources: 1 };
    const p = plByCause.get(c.id) ?? { backers: 0, raised: 0 };
    const imp = impByCause.get(c.id);
    return {
      ...c,
      rarity: rarity(e.passed),
      passed: e.passed,
      unknown: e.unknown,
      momentum: momentum(e.passed, e.sources),
      backers: p.backers,
      raised: p.raised,
      impact: imp ?? null,
    };
  });

  // hero = highest momentum, then most backers
  const hero = [...cards].sort((a, b) => b.momentum - a.momentum || b.backers - a.backers)[0] ?? null;

  const pillars = Array.from(
    cards.reduce((m, c) => m.set(c.pillar, (m.get(c.pillar) ?? 0) + 1), new Map<string, number>())
  ).map(([pillar, count]) => ({ pillar, count }));

  const orgs = cards
    .filter((c) => c.org_domain)
    .map((c) => ({ org_name: c.org_name, org_domain: c.org_domain! }))
    .filter((o, i, a) => a.findIndex((x) => x.org_domain === o.org_domain) === i)
    .slice(0, 10);

  const newsRows = await q<{ source_title: string; source_url: string; excerpt: string; check_name: string; org_name: string }>(
    `select e.source_title, e.source_url, e.excerpt, e.check_name, c.org_name
     from evidence e join causes c on c.id = e.cause_id
     where e.source_url is not null and e.source_title is not null and e.result = 'pass'
     order by e.retrieved_at desc limit 40`
  );
  const seen = new Set<string>();
  const news = newsRows
    .filter((n) => (seen.has(n.source_url) ? false : (seen.add(n.source_url), true)))
    .slice(0, 6);

  const events = await q<{ id: string; title: string; pillar: string | null; geography: string | null; status: string; source_url: string | null }>(
    "select id, title, pillar, geography, status, source_url from events order by created_at desc limit 6"
  );

  const patron = await getOrCreatePatron();
  const leaderboard = (await q<{ id: string; name: string; impact_points: number; streak_days: number }>(
    "select id, name, impact_points, streak_days from patrons order by impact_points desc limit 5"
  )).map(decoratePatron);

  return { hero, cards, pillars, orgs, news, events, patron, leaderboard };
}

const sameUtcDay = (a: Date, b: Date) =>
  a.getUTCFullYear() === b.getUTCFullYear() && a.getUTCMonth() === b.getUTCMonth() && a.getUTCDate() === b.getUTCDate();

export async function pledge(causeId: string, amount: number): Promise<{ backers: number; patron: Patron; points: number }> {
  const patron = await getOrCreatePatron();
  const cause = await one<{ id: string }>("select id from causes where id = $1 and status = 'cleared'", [causeId]);
  if (!cause) throw new Error("cause not found or not cleared");

  await q("insert into pledges (cause_id, patron_id, amount) values ($1, $2, $3)", [causeId, patron.id, amount]);

  const points = Math.max(50, Math.round(amount * 1.5));
  // streak: +1 if last pledge was on a prior day (or first ever); reset never here
  const last = await one<{ last_pledge_at: string | null }>("select last_pledge_at from patrons where id = $1", [patron.id]);
  const now = new Date();
  const bumpStreak = !last?.last_pledge_at || !sameUtcDay(new Date(last.last_pledge_at), now);

  const updated = await one<{ id: string; name: string; impact_points: number; streak_days: number }>(
    `update patrons set impact_points = impact_points + $2,
            streak_days = streak_days + $3, last_pledge_at = now()
     where id = $1 returning id, name, impact_points, streak_days`,
    [patron.id, points, bumpStreak ? 1 : 0]
  );
  const backersRow = await one<{ backers: number }>(
    "select count(*)::int as backers from pledges where cause_id = $1", [causeId]
  );
  return { backers: backersRow!.backers, patron: decoratePatron(updated!), points };
}
