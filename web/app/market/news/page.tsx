"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Capybara } from "@/components/Capybara";
import "../market.css";

interface NewsItem {
  id: string; kind: "article" | "video"; title: string; source: string | null; url: string;
  image_url: string | null; excerpt: string | null; published: string | null; pillar: string | null; video_id: string | null;
}
interface Feed { articles: NewsItem[]; videos: NewsItem[]; pillars: string[] }

function imgErr(e: { currentTarget: HTMLImageElement }) { e.currentTarget.style.display = "none"; }
function host(u: string): string { try { return new URL(u).host.replace(/^www\./, ""); } catch { return "source"; } }

export default function News() {
  const [f, setF] = useState<Feed | null>(null);
  const [pillar, setPillar] = useState<string | null>(null);
  const [playing, setPlaying] = useState<string | null>(null);

  useEffect(() => { fetch("/api/market/news", { cache: "no-store" }).then((r) => r.json()).then(setF); }, []);

  if (!f) return <div className="mk"><div className="mk-wrap"><div className="mk-empty">Loading news…</div></div></div>;

  const articles = pillar ? f.articles.filter((a) => a.pillar === pillar) : f.articles;
  const videos = pillar ? f.videos.filter((v) => v.pillar === pillar) : f.videos;
  const featured = articles.find((a) => a.image_url) ?? articles[0];
  const rest = articles.filter((a) => a.id !== featured?.id);

  return (
    <div className="mk">
      <div className="mk-wrap">
        <header className="mk-top mk-glass" style={{ marginBottom: 18 }}>
          <Link href="/market" className="mk-brand"><span className="mk-logo"><Capybara size={24} /></span><span><b>YourDues</b><span className="eyebrow">Verified causes</span></span></Link>
          <nav className="mk-nav">
            <Link href="/market"><button>Causes</button></Link>
            <Link href="/market"><button>Events</button></Link>
            <button className="on">News</button>
            <Link href="/market"><button>Leaderboard</button></Link>
          </nav>
          <div className="mk-spacer" />
          <Link href="/market" className="mk-chip">← Marketplace</Link>
        </header>

        <div className="mk-sechead" style={{ marginBottom: 14 }}>
          <h1 style={{ fontSize: 26 }}>📰 News &amp; stories</h1>
          <span className="mk-chip">{f.articles.length + f.videos.length} items</span>
        </div>

        <div className="mk-fchips" style={{ marginBottom: 20 }}>
          <button className={!pillar ? "on" : ""} onClick={() => setPillar(null)}>All</button>
          {f.pillars.map((p) => <button key={p} className={pillar === p ? "on" : ""} onClick={() => setPillar(pillar === p ? null : p)}>{p}</button>)}
        </div>

        {featured && (
          <motion.a className="mk-newshero mk-glass" href={featured.url} target="_blank" rel="noreferrer"
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .45 }}>
            <div className="mk-newshero-img">
              {featured.image_url && <img src={featured.image_url} alt="" onError={imgErr} />}
              <div className="mk-art-shade" />
            </div>
            <div className="mk-newshero-body">
              <div className="mk-newsmeta"><span className="dot" />{featured.source || host(featured.url)}{featured.pillar ? ` · ${featured.pillar}` : ""}{featured.published ? ` · ${featured.published}` : ""}</div>
              <h2>{featured.title}</h2>
              {featured.excerpt && <p className="dim">{featured.excerpt}</p>}
              <span className="mk-readmore">Read the story ↗</span>
            </div>
          </motion.a>
        )}

        {rest.length > 0 && <>
          <div className="mk-sechead" style={{ margin: "24px 2px 12px" }}><h2>Latest</h2></div>
          <div className="mk-newsgrid">
            {rest.map((a, i) => (
              <motion.a key={a.id} className="mk-newscard mk-glass" href={a.url} target="_blank" rel="noreferrer"
                initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i * 0.03, 0.25), duration: .35 }}
                whileHover={{ y: -4 }}>
                <div className="mk-newscard-img">
                  {a.image_url ? <img src={a.image_url} alt="" loading="lazy" onError={imgErr} /> : null}
                </div>
                <div className="mk-newscard-body">
                  <div className="mk-newsmeta"><span className="dot" />{a.source || host(a.url)}{a.pillar ? ` · ${a.pillar}` : ""}</div>
                  <h3>{a.title}</h3>
                  {a.excerpt && <p className="dim">{a.excerpt}</p>}
                </div>
              </motion.a>
            ))}
          </div>
        </>}

        {videos.length > 0 && <>
          <div className="mk-sechead" style={{ margin: "26px 2px 12px" }}><h2>▶ Watch</h2></div>
          <div className="mk-vidgrid">
            {videos.map((v) => (
              <div key={v.id} className="mk-vidcard mk-glass">
                {playing === v.id && v.video_id ? (
                  <div className="mk-vidframe">
                    <iframe src={`https://www.youtube.com/embed/${v.video_id}?autoplay=1`} title={v.title}
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
                  </div>
                ) : (
                  <button className="mk-vidthumb" onClick={() => setPlaying(v.id)} aria-label={`Play ${v.title}`}>
                    {v.image_url && <img src={v.image_url} alt="" loading="lazy" onError={imgErr} />}
                    <span className="mk-play">▶</span>
                  </button>
                )}
                <div className="mk-vidbody">
                  <div className="mk-newsmeta"><span className="dot" />{v.source}{v.pillar ? ` · ${v.pillar}` : ""}</div>
                  <h3>{v.title}</h3>
                </div>
              </div>
            ))}
          </div>
        </>}

        <div className="mk-foot">News and video gathered from you.com across YourDues pillars. Stories link to their original sources.</div>
      </div>
    </div>
  );
}
