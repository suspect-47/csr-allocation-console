import { NextResponse } from "next/server";
import { causeDetail } from "@/lib/market";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  const d = await causeDetail(params.id);
  if (!d) return NextResponse.json({ detail: "cause not found" }, { status: 404 });
  return NextResponse.json(d);
}
