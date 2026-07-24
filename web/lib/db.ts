// Postgres access (server only). node-pg returns numeric as string, so read
// queries cast money columns to float8.

import { Pool } from "pg";

let pool: Pool | null = null;

export function db(): Pool {
  if (!pool) {
    pool = new Pool({
      connectionString: process.env.DATABASE_URL ?? "postgresql://csr:csr@localhost:5432/causes",
      max: 10,
      connectionTimeoutMillis: 5000, // fail fast when the DB is down
    });
  }
  return pool;
}

export async function q<T = Record<string, unknown>>(
  text: string,
  params: unknown[] = []
): Promise<T[]> {
  const res = await db().query(text, params as unknown[]);
  return res.rows as T[];
}

export async function one<T = Record<string, unknown>>(
  text: string,
  params: unknown[] = []
): Promise<T | null> {
  const rows = await q<T>(text, params);
  return rows[0] ?? null;
}

export async function dbHealth(): Promise<boolean> {
  try {
    await q("select 1 as ok");
    return true;
  } catch {
    return false;
  }
}
