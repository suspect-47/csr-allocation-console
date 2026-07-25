"use client";

import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { type FormEvent, type ReactNode, useEffect, useRef, useState } from "react";
import "../market.css";

interface Item {
  id?: string; kind?: "article" | "video"; title: string; source: string | null; url: string;
  image_url: string | null; excerpt: string | null; published?: string | null; pillar?: string | null; video_id?: string | null; date?: string | null;
}
interface Feed { articles: Item[]; videos: Item[]; pillars: string[] }
type FundState = "creating" | { id: string; org_name: string } | undefined;

function imgErr(e: { currentTarget: HTMLImageElement }) { e.currentTarget.style.display = "none"; }

// Domain → clean brand name. Known outlets mapped; short call-signs upper-cased.
const BRANDS: Record<string, string> = {
  nytimes: "NYTimes", wsj: "WSJ", bbc: "BBC", cnn: "CNN", npr: "NPR", pbs: "PBS",
  reuters: "Reuters", apnews: "AP News", theguardian: "The Guardian", guardian: "The Guardian",
  washingtonpost: "Washington Post", aljazeera: "Al Jazeera", forbes: "Forbes", bloomberg: "Bloomberg",
  cnbc: "CNBC", abcnews: "ABC News", nbcnews: "NBC News", cbsnews: "CBS News", foxnews: "Fox News",
  usatoday: "USA Today", axios: "Axios", vox: "Vox", politico: "Politico", time: "TIME",
  newsweek: "Newsweek", huffpost: "HuffPost", thehill: "The Hill", nypost: "NY Post",
  theconversation: "The Conversation", propublica: "ProPublica", devex: "Devex", undp: "UNDP",
  unicef: "UNICEF", who: "WHO", worldbank: "World Bank", reliefweb: "ReliefWeb",
  newyorker: "The New Yorker", wishtv: "WISH-TV", krwg: "KRWG", yahoo: "Yahoo", latimes: "LA Times",
  npr_org: "NPR", spectrumnews1: "Spectrum News", people: "People", euronews: "Euronews",
};
function fmtDate(d?: string | null): string { return d ? d.slice(0, 10) : ""; }
function domainOf(src: string | null, url: string): string {
  const h = src && src.includes(".") ? src : (() => { try { return new URL(url).host; } catch { return src || ""; } })();
  return h.replace(/^www\./, "").toLowerCase();
}
function brand(src: string | null, url: string): string {
  const label = domainOf(src, url).split(".")[0] || "Source";
  if (BRANDS[label]) return BRANDS[label];
  if (label.length <= 4) return label.toUpperCase();
  return label.charAt(0).toUpperCase() + label.slice(1);
}
function favicon(src: string | null, url: string): string {
  return `https://www.google.com/s2/favicons?domain=${domainOf(src, url)}&sz=64`;
}
const TONE: Record<string, string> = {
  "Clean Water": "#0ea5e9", Education: "#8b5cf6", Health: "#f43f5e", "Food Security": "#f59e0b",
  "Disaster Relief": "#ef4444", "Poverty Relief": "#10b981", Environment: "#22c55e", Animals: "#f97316",
  Refugees: "#14b8a6", "Mental Health": "#6366f1",
};
function tone(p?: string | null): string { return (p && TONE[p]) || "#10b981"; }

function Badges({ item, onPillar }: { item: Item; onPillar?: (p: string) => void }) {
  return (
    <div className="mk-badges">
      <span className="mk-badge mk-badge--src">
        <img className="mk-badge-logo" src={favicon(item.source, item.url)} alt="" width={16} height={16} onError={imgErr} />
        {brand(item.source, item.url)}
      </span>
      {item.pillar && (onPillar
        ? <button className="mk-badge mk-badge--cat" style={{ ["--tone" as string]: tone(item.pillar) }} onClick={() => onPillar(item.pillar!)}>{item.pillar}</button>
        : <span className="mk-badge mk-badge--cat" style={{ ["--tone" as string]: tone(item.pillar) }}>{item.pillar}</span>)}
      {(item.published || item.date) && <span className="mk-badge mk-badge--date">{fmtDate(item.published || item.date)}</span>}
    </div>
  );
}

export default function News() {
  const [f, setF] = useState<Feed | null>(null);
  const [pillar, setPillar] = useState<string | null>(null);
  const [playing, setPlaying] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Item[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [fund, setFund] = useState<Record<string, FundState>>({});
  const [toasts, setToasts] = useState<{ id: number; node: ReactNode }[]>([]);
  const tidRef = useRef(0);

  useEffect(() => { fetch("/api/market/news", { cache: "no-store" }).then((r) => r.json()).then(setF); }, []);

  function toast(node: ReactNode) {
    const id = ++tidRef.current;
    setToasts((t) => [...t, { id, node }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }

  async function runSearch(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) { setResults(null); return; }
    setSearching(true); setResults([]);
    try {
      const r = await fetch(`/api/market/news/search?q=${encodeURIComponent(q)}`, { cache: "no-store" });
      const d = await r.json();
      setResults(d.results ?? []);
    } catch { setResults([]); toast("Search failed"); }
    setSearching(false);
  }

  async function createFund(item: Item) {
    setFund((s) => ({ ...s, [item.url]: "creating" }));
    try {
      const r = await fetch("/api/market/news/create-fund", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ title: item.title, excerpt: item.excerpt, source: item.source, url: item.url, image_url: item.image_url }),
      });
      if (!r.ok) throw new Error();
      const d = await r.json();
      setFund((s) => ({ ...s, [item.url]: { id: d.id, org_name: d.org_name } }));
      toast(<>✨ Fund created: <b>{d.org_name}</b> · <Link href={`/market/causes/${d.id}`} style={{ color: "var(--accent)", fontWeight: 700 }}>open →</Link></>);
    } catch { setFund((s) => ({ ...s, [item.url]: undefined })); toast("Could not create fund"); }
  }

  function pickPillar(p: string) {
    setResults(null); setQuery("");
    setPillar((cur) => (cur === p ? null : p));
    if (typeof window !== "undefined") window.scrollTo({ top: 0, behavior: "smooth" });
  }

  if (!f) return <div className="mk"><div className="mk-wrap"><div className="mk-empty">Loading news…</div></div></div>;

  const articles = (pillar ? f.articles.filter((a) => a.pillar === pillar) : f.articles);
  const videos = pillar ? f.videos.filter((v) => v.pillar === pillar) : f.videos;
  const featured = articles.find((a) => a.image_url) ?? articles[0];
  const rest = articles.filter((a) => a.id !== featured?.id);
  const searchMode = results !== null;

  return (
    <div className="mk">
      <div className="mk-wrap">
        <header className="mk-top mk-glass" style={{ marginBottom: 18 }}>
          <Link href="/market" className="mk-brand"><span><b>yourDues</b></span></Link>
          <nav className="mk-nav">
            <Link href="/market"><button>Causes</button></Link>
            <Link href="/market"><button>Events</button></Link>
            <button className="on">News</button>
          </nav>
          <div className="mk-spacer" />
          <Link href="/market" className="mk-chip">← Marketplace</Link>
        </header>

        <div className="mk-newshead">
          <h1>📰 News &amp; stories</h1>
          <form className="mk-newssearch" onSubmit={runSearch}>
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" /><path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search the web for any news or story…" aria-label="Search news" />
            {query && <button type="button" className="mk-search-clear" onClick={() => { setQuery(""); setResults(null); }} aria-label="Clear">✕</button>}
            <button type="submit" className="mk-search-go">Search</button>
          </form>
          <span className="mk-chip">{f.articles.length + f.videos.length} items</span>
        </div>

        {!searchMode && (
          <div className="mk-catfilter" style={{ marginBottom: 20 }}>
            <span className="mk-catlabel">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M3 5h18l-7 8v6l-4-2v-4L3 5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" /></svg>
              Category
            </span>
            <div className="mk-fchips">
              <button className={!pillar ? "on" : ""} onClick={() => setPillar(null)}>All</button>
              {f.pillars.map((p) => {
                const n = f.articles.filter((a) => a.pillar === p).length + f.videos.filter((v) => v.pillar === p).length;
                return (
                  <button key={p} className={pillar === p ? "on" : ""} onClick={() => setPillar(pillar === p ? null : p)} style={{ ["--tone" as string]: tone(p) }}>
                    <i className="mk-catdot" />{p}<span>{n}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {searchMode && (
          <section style={{ marginBottom: 8 }}>
            <div className="mk-sechead" style={{ margin: "0 2px 12px" }}>
              <h2>🔎 Web results{query ? <> · <span className="dim">“{query}”</span></> : ""}</h2>
              <span className="mk-chip" onClick={() => { setResults(null); setQuery(""); }} style={{ cursor: "pointer" }}>Clear ✕</span>
            </div>
            {searching ? <div className="mk-empty">Searching the web…</div>
              : results.length ? <div className="mk-newsgrid">{results!.map((r, i) => <NewsCard key={i} item={r} state={fund[r.url]} onFund={createFund} />)}</div>
                : <div className="mk-empty">No results for that search.</div>}
          </section>
        )}

        {!searchMode && featured && (
          <div className="mk-newshero mk-glass">
            <a className="mk-newshero-img" href={featured.url} target="_blank" rel="noreferrer">
              {featured.image_url && <img src={featured.image_url} alt="" onError={imgErr} />}
              <div className="mk-art-shade" />
            </a>
            <div className="mk-newshero-body">
              <Badges item={featured} onPillar={pickPillar} />
              <a href={featured.url} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}><h2>{featured.title}</h2></a>
              {featured.excerpt && <p className="dim">{featured.excerpt}</p>}
              <FundBtn item={featured} state={fund[featured.url]} onFund={createFund} big />
            </div>
          </div>
        )}

        {!searchMode && rest.length > 0 && <>
          <div className="mk-sechead" style={{ margin: "24px 2px 12px" }}><h2>Latest</h2></div>
          <div className="mk-newsgrid">{rest.map((a) => <NewsCard key={a.id} item={a} state={fund[a.url]} onFund={createFund} onPillar={pickPillar} />)}</div>
        </>}

        {!searchMode && videos.length > 0 && <>
          <div className="mk-sechead" style={{ margin: "26px 2px 12px" }}><h2>▶ Watch</h2></div>
          <div className="mk-vidgrid">
            {videos.map((v) => (
              <div key={v.id} className="mk-vidcard mk-glass">
                {playing === v.id && v.video_id ? (
                  <div className="mk-vidframe"><iframe src={`https://www.youtube.com/embed/${v.video_id}?autoplay=1`} title={v.title} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen /></div>
                ) : (
                  <button className="mk-vidthumb" onClick={() => setPlaying(v.id!)} aria-label={`Play ${v.title}`}>
                    {v.image_url && <img src={v.image_url} alt="" loading="lazy" onError={imgErr} />}
                    <span className="mk-play">▶</span>
                  </button>
                )}
                <div className="mk-vidbody">
                  <Badges item={v} onPillar={pickPillar} />
                  <h3>{v.title}</h3>
                </div>
              </div>
            ))}
          </div>
        </>}

        <div className="mk-foot">News and video gathered from you.com. Search pulls live web results; “Create fund” drafts a cause from any story with AI.</div>
      </div>

      <div className="mk-toasts">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div key={t.id} className="mk-toast" initial={{ opacity: 0, y: 14, scale: .96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 10 }}>{t.node}</motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

function FundBtn({ item, state, onFund, big }: { item: Item; state: FundState; onFund: (i: Item) => void; big?: boolean }) {
  if (typeof state === "object") {
    return <Link href={`/market/causes/${state.id}`} className={`mk-fund ${big ? "mk-fund--big" : ""}`}>✓ Fund created — open →</Link>;
  }
  return (
    <button className={`mk-fund ${big ? "mk-fund--big" : ""}`} disabled={state === "creating"} onClick={() => onFund(item)}>
      {state === "creating" ? "Drafting…" : "✨ Create fund"}
    </button>
  );
}

function NewsCard({ item, state, onFund, onPillar }: { item: Item; state: FundState; onFund: (i: Item) => void; onPillar?: (p: string) => void }) {
  return (
    <motion.div className="mk-newscard mk-glass" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .3 }} whileHover={{ y: -3 }}>
      <a className="mk-newscard-img" href={item.url} target="_blank" rel="noreferrer">
        {item.image_url && <img src={item.image_url} alt="" loading="lazy" onError={imgErr} />}
      </a>
      <div className="mk-newscard-body">
        <Badges item={item} onPillar={onPillar} />
        <a href={item.url} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}><h3>{item.title}</h3></a>
        {item.excerpt && <p className="dim">{item.excerpt}</p>}
        <div className="mk-news-actions">
          <FundBtn item={item} state={state} onFund={onFund} />
          <a className="mk-detailbtn" href={item.url} target="_blank" rel="noreferrer" aria-label="Read source">↗</a>
        </div>
      </div>
    </motion.div>
  );
}
