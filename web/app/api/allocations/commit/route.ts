import { NextResponse } from "next/server";
import { validateCommit } from "@/lib/allocation";
import { activeProfiles, clearedCards, insertCommittedAllocations } from "@/lib/repo";
import type { NeedType } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface Body {
  lines: { cause_id: string; amount: number }[];
}

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as Body | null;
  if (!body?.lines) return NextResponse.json({ detail: "no lines" }, { status: 422 });

  const profiles = await activeProfiles();
  if (!profiles.length) return NextResponse.json({ detail: "no profile" }, { status: 400 });
  const profile = profiles[0];

  const cards = await clearedCards();
  const byId = new Map(cards.map((c) => [c.id, c]));
  const devAvailable = cards.some((c) => c.need_type === "development");

  const lines: { cause_id: string; amount: number; need_type: NeedType; rationale: string }[] = [];
  for (const item of body.lines) {
    const card = byId.get(item.cause_id);
    if (!card) {
      return NextResponse.json({ detail: `cause ${item.cause_id} is not cleared` }, { status: 422 });
    }
    lines.push({
      cause_id: item.cause_id,
      amount: Number(item.amount),
      need_type: card.need_type,
      rationale: `Committed allocation for ${card.org_name}.`,
    });
  }

  // AllocationSheet rules: 40% cap, development floor, non-negative remainder.
  const check = validateCommit(
    lines.map((l) => ({ amount: l.amount, need_type: l.need_type })),
    profile.quarterly_budget,
    devAvailable
  );
  if (!check.ok) return NextResponse.json({ detail: check.error }, { status: 422 });

  await insertCommittedAllocations(
    profile.id,
    lines.map((l) => ({ cause_id: l.cause_id, amount: l.amount, rationale: l.rationale }))
  );
  return NextResponse.json({ committed: true, allocated: check.allocated, unallocated: check.unallocated });
}
