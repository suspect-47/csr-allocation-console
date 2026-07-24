import { NextResponse } from "next/server";
import { activeProfiles, createProfile } from "@/lib/repo";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const profiles = await activeProfiles();
  if (!profiles.length) {
    return NextResponse.json({ detail: "no profile — visit setup" }, { status: 404 });
  }
  return NextResponse.json(profiles[0]);
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  const { name, pillars, geographies, quarterly_budget, currency } = body ?? {};
  if (
    !name ||
    !Array.isArray(pillars) ||
    pillars.length === 0 ||
    !Array.isArray(geographies) ||
    geographies.length === 0 ||
    !(Number(quarterly_budget) > 0)
  ) {
    return NextResponse.json({ detail: "invalid profile" }, { status: 422 });
  }
  const id = await createProfile({
    name,
    pillars,
    geographies,
    quarterly_budget: Number(quarterly_budget),
    currency: currency || "USD",
  });
  return NextResponse.json({ id }, { status: 201 });
}
