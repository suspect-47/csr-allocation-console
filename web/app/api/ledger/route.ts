import { NextResponse } from "next/server";
import { blockedCauses } from "@/lib/repo";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(await blockedCauses());
}
