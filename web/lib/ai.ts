// OpenAI (via REST) — drafts a fundable cause from a news story. Reads
// OPENAI_API_KEY from the server env. Model from CREW_MODEL (openai/<model>).

const PILLARS = [
  "Clean Water", "Education", "Health", "Food Security", "Disaster Relief",
  "Poverty Relief", "Environment", "Animals", "Refugees", "Mental Health",
];

export interface FundDraft {
  org_name: string;
  org_domain: string | null;
  pillar: string;
  headline: string;
  blurb: string;
}

const SYS =
  "From a news story about a charitable need, draft a fundable cause. Return " +
  "strict JSON {\"org_name\": string, \"org_domain\": string or empty, " +
  "\"pillar\": one of [" + PILLARS.join(", ") + "], \"headline\": string <=60 " +
  "chars stating what the money does, \"blurb\": string <=120 chars}. Name the " +
  "organization actually involved when the story identifies one; otherwise a " +
  "concise cause name. Use only the story — invent no figures.";

export async function draftFundFromNews(n: { title: string; excerpt: string; source: string; url: string }): Promise<FundDraft> {
  const key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error("OPENAI_API_KEY is not set");
  const model = (process.env.CREW_MODEL || "openai/gpt-4o-mini").replace(/^openai\//, "");

  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${key}` },
    body: JSON.stringify({
      model,
      temperature: 0.2,
      max_tokens: 200,
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: SYS },
        { role: "user", content: `Title: ${n.title}\nSource: ${n.source}\nExcerpt: ${n.excerpt}\nURL: ${n.url}` },
      ],
    }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`openai ${res.status}`);
  const d = (await res.json()) as { choices?: { message?: { content?: string } }[] };
  const data = JSON.parse(d?.choices?.[0]?.message?.content || "{}") as Record<string, string>;
  const pillar = PILLARS.includes(data.pillar) ? data.pillar : "Poverty Relief";
  return {
    org_name: String(data.org_name || "Community cause").slice(0, 60),
    org_domain: data.org_domain ? String(data.org_domain).replace(/^https?:\/\//, "").replace(/\/.*$/, "") : null,
    pillar,
    headline: String(data.headline || "").slice(0, 60),
    blurb: String(data.blurb || "").slice(0, 120),
  };
}
