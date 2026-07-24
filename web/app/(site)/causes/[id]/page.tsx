"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { SkeletonCard } from "@/components/Skeleton";
import { api } from "@/lib/api";
import { hostOf, money } from "@/lib/format";
import type { CauseDetail, CheckOutcome } from "@/lib/types";

const CHIP: Record<CheckOutcome, string> = {
  pass: "chip--cleared",
  fail: "chip--blocked",
  unknown: "chip--unknown",
};

const CHECK_LABELS: Record<string, string> = {
  organization_exists: "1 · Organization exists",
  registration_status: "2 · Registration status",
  independent_corroboration: "3 · Independent corroboration",
  recency: "4 · Recency",
  solicitation_channel: "5 · Solicitation channel",
  contradiction_scan: "6 · Contradiction scan",
};

export default function DossierPage() {
  const params = useParams<{ id: string }>();
  const [d, setD] = useState<CauseDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!params.id) return;
    api.getCause(params.id).then((x) => {
      setD(x);
      setLoading(false);
    });
  }, [params.id]);

  if (loading) return <SkeletonCard />;
  if (!d) return null;

  const c = d.cause;
  return (
    <div>
      <Link href="/" style={{ fontSize: "0.85rem" }}>
        ← Console
      </Link>
      <header style={{ margin: "12px 0 20px" }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <span className={`chip ${c.status === "cleared" ? "chip--cleared" : "chip--blocked"}`}>{c.status}</span>
          {c.blocking_check && <span className="chip chip--blocked">blocked at {c.blocking_check}</span>}
        </div>
        <h1>{c.headline}</h1>
        <p className="measure muted">{c.summary}</p>
        <div className="mono muted" style={{ fontSize: "0.8rem", marginTop: 8 }}>
          {c.org_name} · {c.pillar} · {c.geography} · {c.need_type}
        </div>
      </header>

      <section className="card" style={{ marginBottom: 20 }}>
        <h3>Impact</h3>
        {d.impact && d.impact.is_stated ? (
          <p className="mono">
            {money(d.impact.unit_cost ?? 0, d.impact.currency ?? "USD")} {d.impact.unit_label}{" "}
            {d.impact.stated_by_url && (
              <a href={d.impact.stated_by_url} target="_blank" rel="noreferrer">
                source
              </a>
            )}
          </p>
        ) : (
          <p className="muted">Cost per beneficiary not published.</p>
        )}
      </section>

      <section>
        <h3 style={{ marginBottom: 12 }}>Evidence chain</h3>
        <div className="grid">
          {d.evidence.map((e, i) => (
            <div className="card" key={i}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                <strong style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}>
                  {CHECK_LABELS[e.check_name] ?? e.check_name}
                </strong>
                <span className={`chip ${CHIP[e.result]}`}>{e.result}</span>
              </div>
              {e.excerpt && (
                <p className="measure muted" style={{ fontSize: "0.9rem", margin: "8px 0" }}>
                  {e.excerpt}
                </p>
              )}
              {e.source_url ? (
                <a href={e.source_url} target="_blank" rel="noreferrer" style={{ fontSize: "0.82rem" }}>
                  {e.source_title || hostOf(e.source_url)} ↗
                </a>
              ) : (
                <span className="muted" style={{ fontSize: "0.82rem" }}>
                  No source — recorded as unknown
                </span>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
