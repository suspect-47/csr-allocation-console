import { NextResponse } from "next/server";
import { activeProfiles, clearedCards, listRuns } from "@/lib/repo";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const round2 = (x: number) => Math.round(x * 100) / 100;

export async function GET() {
  const profiles = await activeProfiles();
  const profile = profiles[0] ?? null;
  const cards = await clearedCards();
  const allocated = round2(cards.reduce((a, c) => a + (c.amount ?? 0), 0));
  const budget = profile?.quarterly_budget ?? 0;
  const runs = await listRuns(1);
  return NextResponse.json({
    profile,
    cards,
    allocated,
    unallocated: profile ? round2(budget - allocated) : 0,
    has_run: runs.length > 0,
  });
}
