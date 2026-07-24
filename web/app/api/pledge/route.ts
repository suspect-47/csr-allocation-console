import { NextResponse } from "next/server";
import { pledge } from "@/lib/market";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as { cause_id?: string; amount?: number } | null;
  const causeId = body?.cause_id;
  const amount = Number(body?.amount);
  if (!causeId || !(amount > 0)) {
    return NextResponse.json({ detail: "cause_id and a positive amount are required" }, { status: 422 });
  }
  try {
    return NextResponse.json(await pledge(causeId, amount));
  } catch (e) {
    return NextResponse.json({ detail: String(e) }, { status: 400 });
  }
}
