import { NextResponse } from "next/server";
import { getRun } from "@/lib/repo";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  const run = await getRun(params.id);
  if (!run) return NextResponse.json({ detail: "run not found" }, { status: 404 });
  return NextResponse.json(run);
}
