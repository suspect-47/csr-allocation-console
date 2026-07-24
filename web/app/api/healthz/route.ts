import { NextResponse } from "next/server";
import { dbHealth } from "@/lib/db";
import { kvHealth } from "@/lib/kv";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const [db, kv] = await Promise.all([dbHealth(), kvHealth()]);
  return NextResponse.json({ status: "ok", db, kv });
}
