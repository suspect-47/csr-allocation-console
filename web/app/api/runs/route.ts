import { NextResponse } from "next/server";
import { enqueueJob } from "@/lib/kv";
import { activeProfiles, createRun, listRuns } from "@/lib/repo";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(await listRuns());
}

// Web enqueues, worker executes (spec §1) — a crew never runs in this handler.
export async function POST() {
  const profiles = await activeProfiles();
  if (!profiles.length) {
    return NextResponse.json({ detail: "create a profile before running" }, { status: 400 });
  }
  const run_id = await createRun();
  await enqueueJob({ run_id, profile_id: profiles[0].id });
  return NextResponse.json({ run_id }, { status: 202 });
}
