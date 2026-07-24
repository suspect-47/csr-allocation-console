"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import Link from "next/link";
import { type CSSProperties, type ReactNode, useEffect, useRef, useState } from "react";
import { Capybara } from "@/components/Capybara";
import "./market.css";

// ---- types (mirror lib/market.ts) ----
type Rarity = "legendary" | "rare" | "verified" | "listed";
interface Impact { unit_label: string | null; unit_cost: number | null; is_stated: boolean }
interface Card {
  id: string; org_name: string; org_domain: string | null; headline: string; summary: string;
  pillar: string; geography: string; need_type: "acute" | "development";
  rarity: Rarity; verified: boolean; passed: number; unknown: number; momentum: number;
  backers: number; raised: number; impact: Impact | null;
  image_url: string | null; logo_url: string | null; blurb: string | null; created_at: string;
}
interface Patron { id: string; name: string; impact_points: number; streak_days: number; level: number; level_label: string; xp_into_level: number; xp_for_level: number }
interface News { source_title: string; source_url: string; excerpt: string; check_name: string; org_name: string }
interface Ev { id: string; title: string; pillar: string | null; geography: string | null; status: string; source_url: string | null }
interface Org { org_name: string; org_domain: string; logo_url: string | null }
interface Market { hero: Card | null; cards: Card[]; pillars: { pillar: string; count: number }[]; orgs: Org[]; news: News[]; events: Ev[]; patron: Patron; leaderboard: Patron[] }
function imgErr(e: { currentTarget: HTMLImageElement }) { e.currentTarget.style.display = "none"; }

const TABS = ["Causes", "Events", "News", "Leaderboard"];
const SORTS: { key: string; label: string }[] = [
  { key: "trending", label: "Trending" },
  { key: "backed", label: "Most backed" },
  { key: "newest", label: "Newest" },
  { key: "az", label: "A–Z" },
  { key: "verified", label: "Verified first" },
];
const fmt = (n: number) => n.toLocaleString("en-US");
const money = (n: number) => "$" + n.toLocaleString("en-US", { maximumFractionDigits: 0 });
const initials = (s: string) => s.split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
const suggested = (c: Card) => (c.impact?.is_stated && c.impact.unit_cost ? Math.round(c.impact.unit_cost) : 50);

function pillarKey(p: string): "water" | "health" | "education" | "disaster" {
  const s = p.toLowerCase();
  if (/water|sanitation/.test(s)) return "water";
  if (/health|medical|disease/.test(s)) return "health";
  if (/educat|school|literac/.test(s)) return "education";
  return "disaster";
}
const PILLAR_ICON: Record<string, ReactNode> = {
  water: <path d="M12 3s6 7 6 11a6 6 0 1 1-12 0c0-4 6-11 6-11Z" stroke="#fff" strokeWidth="2" />,
  education: <><path d="M3 8l9-4 9 4-9 4-9-4Z" stroke="#fff" strokeWidth="2" /><path d="M7 11v4c0 1 5 3 5 3s5-2 5-3v-4" stroke="#fff" strokeWidth="2" /></>,
  health: <path d="M12 5v14M5 12h14" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" />,
  disaster: <path d="M12 2 3 7v6c0 5 4 8 9 9 5-1 9-4 9-9V7l-9-5Z" stroke="#fff" strokeWidth="2" />,
};
const check = <svg viewBox="0 0 24 24"><path d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z" fill="#dfffe0" /></svg>;

function useCountUp(value: number, reduce: boolean) {
  const [d, setD] = useState(value);
  const prev = useRef(value);
  useEffect(() => {
    if (reduce) { setD(value); prev.current = value; return; }
    const from = prev.current, to = value, start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / 600);
      setD(Math.round(from + (to - from) * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick); else prev.current = to;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, reduce]);
  return d;
}

export default function Market() {
  const reduce = !!useReducedMotion();
  const [m, setM] = useState<Market | null>(null);
  const [cards, setCards] = useState<Card[]>([]);
  const [patron, setPatron] = useState<Patron | null>(null);
  const [tab, setTab] = useState("Causes");
  const [activePillar, setActivePillar] = useState<string | null>(null);
  const [sort, setSort] = useState("trending");
  const [amount, setAmount] = useState(50);
  const [toasts, setToasts] = useState<{ id: number; node: ReactNode; cls?: string }[]>([]);
  const [funds, setFunds] = useState(0);
  const tid = useRef(0);

  const load = () => fetch("/api/market", { cache: "no-store" }).then((r) => r.json()).then((d: Market) => {
    setM(d); setCards(d.cards); setPatron(d.patron);
  });
  useEffect(() => { load(); }, []);

  const ip = useCountUp(patron?.impact_points ?? 0, reduce);

  function toast(node: ReactNode, cls?: string) {
    const id = ++tid.current;
    setToasts((t) => [...t, { id, node, cls }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 2800);
  }

  async function fund(c: Card, amt: number) {
    // optimistic backer bump
    setCards((cs) => cs.map((x) => (x.id === c.id ? { ...x, backers: x.backers + 1 } : x)));
    try {
      const res = await fetch("/api/pledge", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ cause_id: c.id, amount: amt }),
      });
      if (!res.ok) throw new Error();
      const j = await res.json();
      setPatron(j.patron);
      setCards((cs) => cs.map((x) => (x.id === c.id ? { ...x, backers: j.backers } : x)));
      toast(<>＋<b>{fmt(j.points)} IP</b> · backed {c.org_name}</>);
      const n = funds + 1; setFunds(n);
      if (patron && j.patron.level > patron.level) setTimeout(() => toast(<>◆ <b>Level up — {j.patron.level_label}!</b></>, "pack"), 650);
      if (n === 2) setTimeout(() => toast(<>◆ <b>Pack drop!</b> new causes unlock as runs clear</>, "pack"), 650);
    } catch {
      setCards((cs) => cs.map((x) => (x.id === c.id ? { ...x, backers: Math.max(0, x.backers - 1) } : x)));
      toast("Could not record pledge");
    }
  }

  const shown = (activePillar ? cards.filter((c) => c.pillar === activePillar) : [...cards]).sort((a, b) => {
    switch (sort) {
      case "backed": return b.backers - a.backers;
      case "newest": return (b.created_at || "").localeCompare(a.created_at || "");
      case "az": return a.org_name.localeCompare(b.org_name);
      case "verified": return (b.verified ? 1 : 0) - (a.verified ? 1 : 0) || b.momentum - a.momentum;
      default: return b.momentum - a.momentum || b.backers - a.backers;
    }
  });
  const stagger = (i: number) => (reduce ? {} : { initial: { opacity: 0, y: 16 }, animate: { opacity: 1, y: 0 }, transition: { delay: Math.min(i * 0.04, 0.3), duration: 0.4 } });
  const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });

  if (!m || !patron) return <div className="mk"><div className="mk-wrap"><div className="mk-empty">Loading the marketplace…</div></div></div>;

  const hero = m.hero;
  const xpPct = Math.round((patron.xp_into_level / patron.xp_for_level) * 100);

  return (
    <div className="mk">
      <div className="mk-wrap">
        {/* TOP BAR */}
        <motion.header className="mk-top mk-glass" {...(reduce ? {} : { initial: { opacity: 0, y: -10 }, animate: { opacity: 1, y: 0 } })}>
          <Link href="/market" className="mk-brand">
            <span className="mk-logo"><Capybara size={24} /></span>
            <span><b>YourDues</b><span className="eyebrow">Verified causes</span></span>
          </Link>
          <nav className="mk-nav">
            {TABS.map((t) => (
              <button key={t} className={tab === t ? "on" : ""} onClick={() => { setTab(t); scrollTo("sec-" + t.toLowerCase()); }}>{t}</button>
            ))}
          </nav>
          <div className="mk-spacer" />
          <div className="mk-streak" title="Giving streak">🔥 <b className="num">{patron.streak_days}</b></div>
          <div className="mk-patron">
            <div className="mk-ring" style={{ "--p": xpPct } as CSSProperties}><div className="disc">{patron.level}</div></div>
            <div className="who"><b>{patron.level_label}</b><small className="num">{fmt(ip)} IP</small></div>
          </div>
        </motion.header>

        {/* QUESTS */}
        <section className="mk-quests mk-glass">
          <div className="lab">🎯 Daily quests</div>
          <Quest label="Fund 3 causes" now={Math.min(funds, 3)} max={3} />
          <Quest label="Reach next level" now={xpPct} max={100} unit="%" />
          <Quest label="Keep your streak" now={patron.streak_days} max={Math.max(7, patron.streak_days)} unit=" days" />
        </section>

        <div className="mk-grid">
          {/* LEFT */}
          <div className="mk-col">
            {hero ? <HeroCause c={hero} reduce={reduce} onFund={fund} /> : (
              <div className="mk-hero mk-glass"><div className="mk-empty"><h3>No cleared causes yet</h3><p>Run discovery in the operator console, then verified causes appear here.</p><Link className="mk-chip" href="/" style={{ display: "inline-block", marginTop: 10 }}>Open console →</Link></div></div>
            )}

            {/* EVENTS */}
            <section id="sec-events" className="mk-list mk-glass">
              <div className="mk-sechead" style={{ marginBottom: 6 }}><h2>📅 Live events</h2><span className="mk-chip">All</span></div>
              {m.events.length ? m.events.map((e) => (
                <div className="mk-ev" key={e.id}>
                  <div className="ic"><svg viewBox="0 0 24 24" fill="none">{PILLAR_ICON[pillarKey(e.pillar || "")]}</svg></div>
                  <div><div className="ttl">{e.title}</div><div className="sub">{[e.pillar, e.geography].filter(Boolean).join(" · ")}</div></div>
                  <span className={`st ${e.status}`}>{e.status === "live" ? "● Live" : e.status}</span>
                </div>
              )) : <div className="mk-empty" style={{ padding: 20 }}>No events gathered yet.</div>}
            </section>

            {/* LEADERBOARD */}
            <section id="sec-leaderboard" className="mk-list mk-glass">
              <div className="mk-sechead" style={{ marginBottom: 6 }}><h2>🏆 Top patrons</h2><span className="mk-chip">All time</span></div>
              {m.leaderboard.map((p, i) => (
                <div className={`mk-lbrow ${p.id === patron.id ? "me" : ""}`} key={p.id}>
                  <span className={`mk-rank ${i === 0 ? "g" : ""}`}>{i + 1}</span>
                  <div className="av" style={{ background: grad(p.name) }}>{initials(p.name)}</div>
                  <div><div className="nm">{p.id === patron.id ? "You" : p.name}</div><div className="tier">{p.level_label} · 🔥 {p.streak_days}</div></div>
                  <span className="ip num">{fmt(p.impact_points)}</span>
                </div>
              ))}
            </section>
          </div>

          {/* RIGHT */}
          <div className="mk-col">
            <div id="sec-causes" className="mk-filters">
              <div className="mk-fchips">
                <button className={!activePillar ? "on" : ""} onClick={() => setActivePillar(null)}>All <span>{cards.length}</span></button>
                {m.pillars.map((p) => (
                  <button key={p.pillar} className={activePillar === p.pillar ? "on" : ""} onClick={() => setActivePillar(activePillar === p.pillar ? null : p.pillar)}>{p.pillar} <span>{p.count}</span></button>
                ))}
              </div>
              <div className="mk-sortwrap">
                <span className="mk-sortlabel">Sort</span>
                <select className="mk-sort" value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort causes">
                  {SORTS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                </select>
              </div>
            </div>
            <motion.div className="mk-cards" layout={!reduce}>
              <AnimatePresence>
                {shown.map((c, i) => <CauseCard key={c.id} c={c} i={i} reduce={reduce} onFund={fund} />)}
                {shown.length === 0 && <div className="mk-empty" style={{ gridColumn: "1/-1" }}>No causes in this pillar.</div>}
              </AnimatePresence>
            </motion.div>

            {/* TRENDING ORGS */}
            {m.orgs.length > 0 && <>
              <div className="mk-sechead" style={{ marginTop: 2 }}><h2>Trending orgs</h2><span className="mk-chip">Verified</span></div>
              <div className="mk-orgs mk-glass">
                {m.orgs.map((o) => (
                  <a className="mk-org" key={o.org_domain} href={`https://${o.org_domain}`} target="_blank" rel="noreferrer" title={o.org_name}>
                    <div className="av" style={{ background: grad(o.org_name) }}>
                      {o.logo_url ? <img src={o.logo_url} alt="" onError={imgErr} /> : initials(o.org_name)}
                    </div>
                    <small>{o.org_name}</small>
                  </a>
                ))}
              </div>
            </>}

            {/* WALLET */}
            <section className="mk-wallet mk-glass">
              <h2>⚡ Impact Wallet</h2>
              <div className="lead">Pledge earns Impact Points. Points level you up and keep your streak alive.</div>
              <div className="mk-amts">
                {[25, 50, 100, 250].map((a) => (
                  <div key={a} className={`mk-chip ${amount === a ? "on" : ""}`} onClick={() => setAmount(a)}>{money(a)}</div>
                ))}
              </div>
              <input className="mk-field" defaultValue={hero?.org_name ?? ""} placeholder="Choose a cause…" aria-label="Cause" />
              <div className="mk-wrow">
                <input className="mk-field" placeholder="Match code (2× your impact)" aria-label="Match code" />
                <button className="mk-btn" style={{ flex: "0 0 auto" }} disabled={!hero} onClick={() => hero && fund(hero, amount)}>Pledge {money(amount)}</button>
              </div>
            </section>

            {/* NEWS */}
            <div id="sec-news" className="mk-sechead" style={{ marginTop: 2 }}><h2>📰 From the evidence trail</h2><span className="mk-chip">Latest</span></div>
            <div className="mk-news">
              {m.news.length ? m.news.map((n, i) => (
                <motion.a className="mk-ncard mk-glass" key={i} href={n.source_url} target="_blank" rel="noreferrer" {...stagger(i)} {...(reduce ? {} : { whileHover: { y: -3 } })}>
                  <div className="src"><span className="dot" />{host(n.source_url)}</div>
                  <h3>{n.source_title}</h3>
                  <p>{n.excerpt || `${n.org_name} · ${n.check_name.replace(/_/g, " ")}`}</p>
                </motion.a>
              )) : <div className="mk-empty" style={{ gridColumn: "1/-1" }}>News appears from the verification evidence trail.</div>}
            </div>
          </div>
        </div>

        <div className="mk-foot">YourDues · every cause cleared a 6-point verification chain — registration, independent corroboration, and an adversarial fraud scan. No cause ships without evidence.</div>
      </div>

      <div className="mk-toasts">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div key={t.id} className={`mk-toast ${t.cls || ""}`}
              initial={reduce ? {} : { opacity: 0, y: 14, scale: .96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={reduce ? {} : { opacity: 0, y: 10 }}>{t.node}</motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

// ---- sub-components ----
function Quest({ label, now, max, unit = "" }: { label: string; now: number; max: number; unit?: string }) {
  return (
    <div className="mk-quest">
      <b>{label}</b>
      <div className="mk-qbar"><motion.i initial={{ width: 0 }} animate={{ width: `${Math.min(100, (now / max) * 100)}%` }} transition={{ duration: .9, ease: [.2, .7, .2, 1] }} style={{ display: "block", height: "100%", borderRadius: 6, background: "linear-gradient(90deg,var(--impact),var(--accent-2))" }} /></div>
      <small className="num">{now}{unit === "%" || unit === "" ? unit : ""} / {unit === "%" ? "100%" : max + unit}</small>
    </div>
  );
}

function HeroCause({ c, reduce, onFund }: { c: Card; reduce: boolean; onFund: (c: Card, a: number) => void }) {
  const slots = Array.from({ length: 6 }, (_, i) => (i < c.passed ? "pass" : i < c.passed + c.unknown ? "unk" : ""));
  return (
    <motion.article className="mk-hero mk-glass" {...(reduce ? {} : { initial: { opacity: 0, y: 18 }, animate: { opacity: 1, y: 0 }, transition: { duration: .5 } })}>
      <div className="mk-art" style={{ background: grad(c.org_name) }}>
        {c.image_url && <img className="mk-art-img" src={c.image_url} alt="" onError={imgErr} />}
        <div className="mk-art-shade" />
        <div className="tags">
          <span className={`mk-tag ${c.verified ? (c.rarity === "legendary" ? "leg" : "rare") : ""}`}>◆ {c.verified ? c.rarity : "Listed"}</span>
          <span className="mk-tag">{c.pillar} · {c.geography}</span>
        </div>
        <div>
          {c.logo_url && <img className="mk-art-logo" src={c.logo_url} alt="" onError={imgErr} />}
          <div className="big">{c.org_name}</div>
          {c.verified && <div className="mk-crest" title="6-check verification">{slots.map((s, i) => <i key={i} className={s}>{s === "pass" ? check : s === "unk" ? <svg viewBox="0 0 24 24"><path d="M12 3v10" stroke="#ffe6b0" strokeWidth="2.4" strokeLinecap="round" /><circle cx="12" cy="18" r="1.4" fill="#ffe6b0" /></svg> : null}</i>)}</div>}
        </div>
      </div>
      <div className="body">
        <h1>{c.headline}</h1>
        <div className="mk-metrics">
          <div className="mk-metric"><b className="num">{fmt(c.backers)}</b><small>Backers</small></div>
          {c.verified
            ? <><div className="mk-metric"><b className="num">{c.passed} / 6</b><small>Checks passed</small></div><div className="mk-metric"><b className="num">{c.momentum}</b><small>Momentum</small></div></>
            : <><div className="mk-metric"><b>{c.pillar}</b><small>Pillar</small></div><div className="mk-metric"><b>◇ Listed</b><small>Verification pending</small></div></>}
        </div>
        <p className="dim" style={{ margin: "0 0 4px" }}>{c.blurb || c.summary}</p>
        <div className="mk-price">{c.impact?.is_stated && c.impact.unit_cost ? <><b className="num">{money(c.impact.unit_cost)}</b><span className="per">{c.impact.unit_label}</span></> : <span className="per">Cost per beneficiary not published</span>}<span className="match">2× matched</span></div>
        <div className="mk-cta">
          <button className="mk-btn" onClick={() => onFund(c, suggested(c))}>Fund this cause</button>
          <Link className="mk-btn ghost" href={`/market/causes/${c.id}`}>View cause</Link>
        </div>
      </div>
    </motion.article>
  );
}

function CauseCard({ c, i, reduce, onFund }: { c: Card; i: number; reduce: boolean; onFund: (c: Card, a: number) => void }) {
  return (
    <motion.article layout={!reduce} className={`mk-card mk-glass ${c.rarity}`}
      initial={reduce ? false : { opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={reduce ? {} : { opacity: 0, scale: .96 }}
      transition={{ delay: Math.min(i * 0.04, 0.3), duration: .4 }} {...(reduce ? {} : { whileHover: { y: -5 } })}>
      <div className="mk-cart" style={{ background: grad(c.org_name) }}>
        {c.image_url && <img className="mk-cart-img" src={c.image_url} alt="" loading="lazy" onError={imgErr} />}
        <div className="mk-cart-shade" />
        <div className="mk-rar" />
        {c.verified && c.momentum >= 85 && <span className="mk-hot">🔥 Hot</span>}
        {c.verified && <span className={`mk-rtag ${c.rarity}`}>{c.rarity}</span>}
        <span className="mk-pill">{c.pillar}</span>
        <div className="mk-namewrap">
          {c.logo_url && <img className="mk-logo-badge" src={c.logo_url} alt="" onError={imgErr} />}
          <div className="nm">{c.org_name}</div>
        </div>
      </div>
      <div className="mk-info">
        <div className="t">{c.headline}</div>
        <div className="d">{c.blurb || c.summary}</div>
        {c.verified && <div className="mk-mom"><motion.i initial={{ width: 0 }} animate={{ width: `${c.momentum}%` }} transition={{ duration: .8 }} style={{ display: "block", height: "100%", borderRadius: 5, background: "linear-gradient(90deg,var(--impact),var(--gold))" }} /></div>}
        <div className="mk-row"><span className="bk num">{fmt(c.backers)} backers</span><Link href={`/market/causes/${c.id}`} style={{ fontSize: 11, color: "var(--ink-dim)" }}>Details →</Link></div>
        <div className="mk-row" style={{ marginTop: 8 }}>
          <span className="pr num">{c.impact?.is_stated && c.impact.unit_cost ? <>{money(c.impact.unit_cost)} <small>{c.impact.unit_label}</small></> : <small className="faint">Any amount</small>}</span>
          <button className="mk-fund" onClick={() => onFund(c, suggested(c))}>Fund</button>
        </div>
      </div>
    </motion.article>
  );
}

// deterministic gradient from a name (stable per org)
function grad(name: string): string {
  let h = 0; for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360;
  const a = h, b = (h + 40) % 360;
  return `linear-gradient(150deg, hsl(${a} 55% 32%), hsl(${b} 60% 18%))`;
}
function host(u: string): string { try { return new URL(u).host.replace(/^www\./, ""); } catch { return "source"; } }
