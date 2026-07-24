// Allocation constraints (spec §3.5), enforced server-side on commit — the same
// rules the Python AllocationSheet validator enforces. A bad drag is rejected here.

import type { NeedType } from "./types";

export const MAX_SINGLE_CAUSE_SHARE = 0.4;
export const MIN_DEVELOPMENT_SHARE = 0.2;

const round2 = (x: number) => Math.round(x * 100) / 100;

export interface CommitLine {
  amount: number;
  need_type: NeedType;
}

export interface CommitCheck {
  ok: boolean;
  error?: string;
  allocated: number;
  unallocated: number;
}

export function validateCommit(lines: CommitLine[], budget: number, devAvailable: boolean): CommitCheck {
  const allocated = round2(lines.reduce((a, l) => a + l.amount, 0));
  const unallocated = round2(budget - allocated);

  if (allocated - budget > 1e-6) {
    return { ok: false, error: "allocated total exceeds quarterly budget", allocated, unallocated };
  }
  if (unallocated < -1e-6) {
    return { ok: false, error: "remainder cannot be negative", allocated, unallocated };
  }
  const cap = budget * MAX_SINGLE_CAUSE_SHARE;
  for (const l of lines) {
    if (l.amount - cap > 1e-6) {
      return { ok: false, error: `a cause exceeds the ${Math.round(MAX_SINGLE_CAUSE_SHARE * 100)}% cap`, allocated, unallocated };
    }
  }
  if (devAvailable && lines.length) {
    const dev = lines.filter((l) => l.need_type === "development").reduce((a, l) => a + l.amount, 0);
    if (dev + 1e-6 < budget * MIN_DEVELOPMENT_SHARE) {
      return { ok: false, error: `development share below ${Math.round(MIN_DEVELOPMENT_SHARE * 100)}% of budget`, allocated, unallocated };
    }
  }
  return { ok: true, allocated, unallocated: Math.max(0, unallocated) };
}
