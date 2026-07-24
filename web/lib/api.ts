// Client-side fetch layer. Calls the Next.js route handlers under /api.

import type { CauseDetail, ConsoleData, LedgerItem, Profile, Run } from "./types";

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  async getProfile(): Promise<Profile | null> {
    const res = await fetch("/api/profile", { cache: "no-store" });
    if (res.status === 404) return null;
    return j<Profile>(res);
  },
  createProfile(body: Omit<Profile, "id">): Promise<{ id: string }> {
    return fetch("/api/profile", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<{ id: string }>);
  },
  getConsole: (): Promise<ConsoleData> => fetch("/api/console", { cache: "no-store" }).then(j<ConsoleData>),
  getCause: (id: string): Promise<CauseDetail> => fetch(`/api/causes/${id}`, { cache: "no-store" }).then(j<CauseDetail>),
  getLedger: (): Promise<LedgerItem[]> => fetch("/api/ledger", { cache: "no-store" }).then(j<LedgerItem[]>),
  triggerRun: (): Promise<{ run_id: string }> =>
    fetch("/api/runs", { method: "POST" }).then(j<{ run_id: string }>),
  getRun: (id: string): Promise<Run> => fetch(`/api/runs/${id}`, { cache: "no-store" }).then(j<Run>),
  getRuns: (): Promise<Run[]> => fetch("/api/runs", { cache: "no-store" }).then(j<Run[]>),
  commit(lines: { cause_id: string; amount: number }[]): Promise<{ committed: boolean; allocated: number; unallocated: number }> {
    return fetch("/api/allocations/commit", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ lines }),
    }).then(j<{ committed: boolean; allocated: number; unallocated: number }>);
  },
};
