import { NextResponse } from "next/server";
import { searchNews } from "@/lib/youcom";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const q = new URL(req.url).searchParams.get("q")?.trim();
  if (!q) return NextResponse.json({ results: [] });
  try {
    return NextResponse.json({ results: await searchNews(q) });
  } catch (e) {
    return NextResponse.json({ detail: String(e) }, { status: 502 });
  }
}
