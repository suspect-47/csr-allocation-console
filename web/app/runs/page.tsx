"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SkeletonCard } from "@/components/Skeleton";
import { api } from "@/lib/api";
import { shortDate } from "@/lib/format";
import type { Run } from "@/lib/types";

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[] | null>(null);
  useEffect(() => {
    api.getRuns().then(setRuns);
  }, []);
  if (runs === null) return <SkeletonCard />;

  return (
    <div>
      <h1 style={{ marginBottom: 20 }}>Runs</h1>
      {runs.length === 0 ? (
        <div className="empty">
          <h3>No runs yet</h3>
          <p className="muted">Trigger discovery from the console.</p>
        </div>
      ) : (
        <div className="grid">
          {runs.map((r) => (
            <Link key={r.id} href={`/runs/${r.id}`} className="card" style={{ textDecoration: "none", display: "block" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="mono" style={{ fontSize: "0.85rem" }}>
                  {r.id.slice(0, 8)}
                </span>
                <span className={`chip ${r.status === "succeeded" ? "chip--cleared" : r.status === "failed" ? "chip--blocked" : "chip--unknown"}`}>
                  {r.status}
                </span>
              </div>
              <div className="mono muted" style={{ fontSize: "0.8rem", marginTop: 8 }}>
                {shortDate(r.started_at)} · found {r.found ?? 0} · cleared {r.cleared ?? 0} · blocked {r.blocked ?? 0} · {r.tool_calls ?? 0} tool calls
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
