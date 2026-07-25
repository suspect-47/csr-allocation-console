import { NextResponse } from "next/server";
import { draftFundFromNews } from "@/lib/ai";
import { one, q } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface Body { title?: string; excerpt?: string; source?: string; url?: string; image_url?: string | null }

export async function POST(req: Request) {
  const n = (await req.json().catch(() => null)) as Body | null;
  if (!n?.title || !n?.url) {
    return NextResponse.json({ detail: "title and url are required" }, { status: 422 });
  }
  try {
    const draft = await draftFundFromNews({ title: n.title, excerpt: n.excerpt || "", source: n.source || "", url: n.url });
    const row = await one<{ id: string }>(
      `insert into causes
         (org_name, org_domain, headline, summary, blurb, geography, pillar, need_type, status, image_url, created_at)
       values ($1, $2, $3, $4, $5, 'Global', $6, 'development', 'listed', $7, now())
       returning id`,
      [draft.org_name, draft.org_domain, draft.headline || draft.blurb || draft.org_name,
        `${draft.org_name} · ${draft.pillar}. Created from a news story with AI.`, draft.blurb, draft.pillar, n.image_url || null]
    );
    await q(
      `insert into evidence (cause_id, check_name, result, source_url, source_title, excerpt, retrieved_at)
       values ($1, 'ai_from_news', 'pass', $2, $3, $4, now())`,
      [row!.id, n.url, n.title, (n.excerpt || "").slice(0, 200)]
    );
    return NextResponse.json({ id: row!.id, ...draft });
  } catch (e) {
    return NextResponse.json({ detail: String(e) }, { status: 502 });
  }
}
