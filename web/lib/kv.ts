// Render Key Value (Redis) — job queue. Same key + JSON shape the Python worker
// consumes (spec §1): web LPUSHes, worker BRPOPs.

import Redis from "ioredis";

let client: Redis | null = null;
const QUEUE_KEY = "csr:jobs";

export function kv(): Redis {
  if (!client) {
    client = new Redis(process.env.KV_URL ?? "redis://localhost:6379/0", {
      maxRetriesPerRequest: 2,
    });
    client.on("error", () => {}); // avoid unhandled error events when KV is down
  }
  return client;
}

export async function enqueueJob(job: { run_id: string; profile_id: string }): Promise<void> {
  await kv().lpush(QUEUE_KEY, JSON.stringify(job));
}

export async function kvHealth(): Promise<boolean> {
  try {
    return (await kv().ping()) === "PONG";
  } catch {
    return false;
  }
}
