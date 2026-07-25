// Node-side you.com Search for live, on-demand news (the Python client is not
// reachable from the Next API). Reads YOU_SEARCH_API_KEY from the server env.

const BASE = process.env.YOU_SEARCH_BASE_URL || "https://ydc-index.io";

export interface WebNews {
  title: string;
  url: string;
  source: string;
  excerpt: string;
  image_url: string | null;
  date: string | null;
  kind: "article";
}

function hostOf(u: string): string {
  try {
    return new URL(u).host.replace(/^www\./, "");
  } catch {
    return "source";
  }
}

export async function searchNews(query: string): Promise<WebNews[]> {
  const key = process.env.YOU_SEARCH_API_KEY;
  if (!key) throw new Error("YOU_SEARCH_API_KEY is not set");
  const url = `${BASE}/v1/search?` + new URLSearchParams({ query, count: "16", freshness: "month" });
  const res = await fetch(url, { headers: { "X-API-Key": key }, cache: "no-store" });
  if (!res.ok) throw new Error(`you.com search ${res.status}`);
  const d = (await res.json()) as { results?: { news?: unknown[]; web?: unknown[] } };
  const raw = (d?.results?.news?.length ? d.results.news : d?.results?.web) ?? [];
  const out: WebNews[] = [];
  const seen = new Set<string>();
  for (const item of raw as Record<string, unknown>[]) {
    const u = String(item.url || "");
    const title = String(item.title || "");
    if (!u || !title || seen.has(u)) continue;
    seen.add(u);
    const snips = Array.isArray(item.snippets) ? (item.snippets as unknown[]).join(" ") : "";
    out.push({
      title,
      url: u,
      source: hostOf(u),
      excerpt: String(item.description || snips || "").slice(0, 300),
      image_url: (item.thumbnail_url as string) || null,
      date: (item.page_age as string) || null,
      kind: "article",
    });
  }
  return out;
}
