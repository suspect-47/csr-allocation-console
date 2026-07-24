"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Capybara } from "@/components/Capybara";
import "../../market.css";

const fmt = (n: number) => n.toLocaleString("en-US");
const money = (n: number) => "$" + n.toLocaleString("en-US", { maximumFractionDigits: 0 });
function imgErr(e: { currentTarget: HTMLImageElement }) { e.currentTarget.style.display = "none"; }
function grad(name: string): string {
  let h = 0; for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360;
  return `linear-gradient(150deg, hsl(${h} 55% 32%), hsl(${(h + 40) % 360} 60% 18%))`;
}
const CHECK_LABELS: Record<string, string> = {
  organization_exists: "1 · Organization exists",
  registration_status: "2 · Registration",
  independent_corroboration: "3 · Independent corroboration",
  recency: "4 · Recency",
  solicitation_channel: "5 · Solicitation channel",
  contradiction_scan: "6 · Adversarial fraud scan",
};
const RESCOLOR: Record<string, string> = { pass: "var(--impact)", fail: "var(--coral)", unknown: "var(--gold)" };

interface Detail {
  cause: { id: string; org_name: string; org_domain: string | null; headline: string; summary: string; blurb: string | null;
    pillar: string; geography: string; status: string; verified: boolean; rarity: string; passed: number; unknown: number;
    momentum: number; backers: number; image_url: string | null; logo_url: string | null;
    impact: { unit_label: string | null; unit_cost: number | null; is_stated: boolean; stated_by_url: string | null } | null; };
  evidence: { check_name: string; result: "pass" | "fail" | "unknown"; source_url: string | null; source_title: string | null; excerpt: string }[];
  directory: { source_url: string | null; source_title: string | null; excerpt: string } | null;
  related: { id: string; org_name: string; pillar: string; image_url: string | null; logo_url: string | null; status: string }[];
}

export default function CausePage() {
  const { id } = useParams<{ id: string }>();
  const [d, setD] = useState<Detail | null>(null);
  const [amount, setAmount] = useState(50);
  const [backers, setBackers] = useState(0);
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!id) return;
    fetch(`/api/market/cause/${id}`, { cache: "no-store" }).then((r) => r.json()).then((x: Detail) => { setD(x); setBackers(x.cause.backers); });
  }, [id]);

  async function fund() {
    if (!d) return;
    setBackers((b) => b + 1);
    try {
      const res = await fetch("/api/pledge", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ cause_id: d.cause.id, amount }) });
      if (!res.ok) throw new Error();
      const j = await res.json();
      setBackers(j.backers);
      setNote(`＋${fmt(j.points)} IP · thank you for backing ${d.cause.org_name}`);
      setTimeout(() => setNote(""), 3000);
    } catch { setBackers((b) => Math.max(0, b - 1)); setNote("Could not record pledge"); }
  }

  if (!d) return <div className="mk"><div className="mk-wrap"><div className="mk-empty">Loading cause…</div></div></div>;
  const c = d.cause;

  return (
    <div className="mk">
      <div className="mk-wrap">
        <header className="mk-top mk-glass" style={{ marginBottom: 18 }}>
          <Link href="/market" className="mk-brand"><span className="mk-logo"><Capybara size={24} /></span><span><b>YourDues</b><span className="eyebrow">Verified causes</span></span></Link>
          <div className="mk-spacer" />
          <Link href="/market" className="mk-chip">← Back to marketplace</Link>
        </header>

        {/* BANNER */}
        <motion.div className="mk-banner mk-glass" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .5 }}>
          <div className="mk-banner-art" style={{ background: grad(c.org_name) }}>
            {c.image_url && <img className="mk-art-img" src={c.image_url} alt="" onError={imgErr} />}
            <div className="mk-art-shade" />
            <div className="mk-banner-inner">
              <div className="tags">
                <span className={`mk-tag ${c.verified ? (c.rarity === "legendary" ? "leg" : "rare") : ""}`}>◆ {c.verified ? c.rarity : "Listed"}</span>
                <span className="mk-tag">{c.pillar} · {c.geography}</span>
              </div>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 14 }}>
                {c.logo_url && <img className="mk-art-logo" src={c.logo_url} alt="" onError={imgErr} style={{ marginBottom: 0 }} />}
                <div className="big" style={{ fontFamily: "var(--fd)", fontWeight: 800, fontSize: "clamp(28px,5vw,52px)", color: "#fff", letterSpacing: "-.03em", lineHeight: .95 }}>{c.org_name}</div>
              </div>
            </div>
          </div>
        </motion.div>

        <div className="mk-two">
          {/* MAIN */}
          <div className="mk-col" style={{ minWidth: 0 }}>
            <section className="mk-glass" style={{ padding: 20 }}>
              <h2 style={{ fontSize: 20, marginBottom: 8 }}>{c.headline}</h2>
              <p className="dim measure" style={{ margin: 0 }}>{c.summary}</p>
            </section>

            <section>
              <div className="mk-sechead"><h2>{c.verified ? "Evidence chain" : "Provenance"}</h2>{c.verified && <span className="mk-chip">{c.passed}/6 passed</span>}</div>
              {c.verified ? (
                <div className="mk-evgrid">
                  {d.evidence.map((e, i) => (
                    <div className="mk-glass mk-evc" key={i}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                        <strong style={{ fontFamily: "var(--fm)", fontSize: 12.5 }}>{CHECK_LABELS[e.check_name] ?? e.check_name}</strong>
                        <span style={{ fontFamily: "var(--fm)", fontSize: 10, textTransform: "uppercase", padding: "3px 8px", borderRadius: 999, border: "1px solid currentColor", color: RESCOLOR[e.result] }}>{e.result}</span>
                      </div>
                      {e.excerpt && <p className="dim" style={{ fontSize: 12, margin: "8px 0" }}>{e.excerpt}</p>}
                      {e.source_url ? <a href={e.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 11.5, color: "var(--impact)" }}>{e.source_title || "source"} ↗</a> : <span className="faint" style={{ fontSize: 11.5 }}>no source — unknown</span>}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mk-glass" style={{ padding: 16 }}>
                  <p className="dim" style={{ marginTop: 0 }}>◇ Listed from a top-charity directory. It has not yet been through the full 6-check verification pipeline.</p>
                  {d.directory?.source_url && <a href={d.directory.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: "var(--impact)" }}>{d.directory.source_title || "source"} ↗</a>}
                </div>
              )}
            </section>

            {d.related.length > 0 && (
              <section>
                <div className="mk-sechead"><h2>More in {c.pillar}</h2></div>
                <div className="mk-relgrid">
                  {d.related.map((r) => (
                    <Link key={r.id} href={`/market/causes/${r.id}`} className="mk-glass mk-rel">
                      <div className="mk-rel-art" style={{ background: grad(r.org_name) }}>
                        {r.image_url && <img className="mk-art-img" src={r.image_url} alt="" onError={imgErr} />}
                        <div className="mk-art-shade" />
                        <span style={{ position: "relative", zIndex: 2, fontFamily: "var(--fd)", fontWeight: 800, color: "#fff", fontSize: 14 }}>{r.org_name}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </div>

          {/* FUND PANEL */}
          <aside className="mk-col">
            <section className="mk-glass" style={{ padding: 18, position: "sticky", top: 84 }}>
              <div className="mk-metrics" style={{ marginTop: 0 }}>
                <div className="mk-metric"><b className="num">{fmt(backers)}</b><small>Backers</small></div>
                {c.verified
                  ? <><div className="mk-metric"><b className="num">{c.passed}/6</b><small>Checks</small></div><div className="mk-metric"><b className="num">{c.momentum}</b><small>Momentum</small></div></>
                  : <div className="mk-metric"><b>◇ Listed</b><small>Verify pending</small></div>}
              </div>
              <div className="mk-price" style={{ margin: "14px 0" }}>
                {c.impact?.is_stated && c.impact.unit_cost ? <><b className="num">{money(c.impact.unit_cost)}</b><span className="per">{c.impact.unit_label}</span></> : <span className="per">Any amount helps</span>}
                <span className="match">2× matched</span>
              </div>
              <div className="mk-amts">
                {[25, 50, 100, 250].map((a) => <div key={a} className={`mk-chip ${amount === a ? "on" : ""}`} onClick={() => setAmount(a)} style={{ flex: 1, justifyContent: "center", display: "flex" }}>{money(a)}</div>)}
              </div>
              <button className="mk-btn" style={{ width: "100%" }} onClick={fund}>Fund {money(amount)}</button>
              {note && <div className="mk-listbadge" style={{ textAlign: "center", marginTop: 10 }} role="status">{note}</div>}
              {c.org_domain && <a href={`https://${c.org_domain}`} target="_blank" rel="noreferrer" style={{ display: "block", textAlign: "center", marginTop: 12, fontSize: 12, color: "var(--ink-dim)" }}>Visit {c.org_domain} ↗</a>}
            </section>
          </aside>
        </div>
        <div className="mk-foot">Pledges produce a sourced pledge sheet — no payment is taken. Every verified cause cleared a 6-point chain.</div>
      </div>
    </div>
  );
}
