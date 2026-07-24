"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SkeletonCard } from "@/components/Skeleton";
import { api } from "@/lib/api";
import type { LedgerItem, Run } from "@/lib/types";

// Did not clear. This route is the proof the system works (spec §5).
export default function LedgerPage() {
  const [items, setItems] = useState<LedgerItem[] | null>(null);
  const [lastRun, setLastRun] = useState<Run | null>(null);

  useEffect(() => {
    api.getLedger().then(setItems);
    api.getRuns().then((rs) => setLastRun(rs[0] ?? null));
  }, []);

  if (items === null) return <SkeletonCard />;

  return (
    <div>
      <header style={{ marginBottom: 20 }}>
        <h1>Did not clear</h1>
        <p className="measure muted">
          Every blocked cause carries its full evidence chain and the check that stopped it. The
          blocked records are product, not waste.
        </p>
      </header>

      {items.length === 0 ? (
        <div className="empty">
          <h3>No causes have been blocked this quarter</h3>
          {lastRun ? (
            <Link className="btn btn--ghost" href={`/runs/${lastRun.id}`}>
              View the last run
            </Link>
          ) : (
            <p className="muted">No runs yet.</p>
          )}
        </div>
      ) : (
        <div className="grid cols-2">
          {items.map((it) => (
            <article className="card" key={it.id}>
              <span className="chip chip--blocked">blocked · {it.blocking_check ?? "unknown"}</span>
              <h3 style={{ marginTop: 8 }}>{it.headline}</h3>
              <p className="measure muted" style={{ fontSize: "0.95rem" }}>
                {it.summary}
              </p>
              <div className="mono muted" style={{ fontSize: "0.8rem", margin: "8px 0" }}>
                {it.pillar} · {it.geography} · {it.need_type}
              </div>
              <Link href={`/causes/${it.id}`} style={{ fontSize: "0.85rem" }}>
                See why it was blocked →
              </Link>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
