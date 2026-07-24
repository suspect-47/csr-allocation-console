"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { SkeletonCard } from "@/components/Skeleton";
import { api } from "@/lib/api";
import { shortDate } from "@/lib/format";
import type { Run } from "@/lib/types";

const STAGES = ["scout", "verify", "score", "compose", "allocate"];
const LIVE = new Set(["queued", "running"]);

export default function RunTracePage() {
  const params = useParams<{ id: string }>();
  const [run, setRun] = useState<Run | null>(null);

  useEffect(() => {
    if (!params.id) return;
    let active = true;
    const tick = async () => {
      const r = await api.getRun(params.id);
      if (!active) return;
      setRun(r);
      if (LIVE.has(r.status)) setTimeout(tick, 2000); // live status while in flight
    };
    tick();
    return () => {
      active = false;
    };
  }, [params.id]);

  if (!run) return <SkeletonCard />;

  const timings = new Map((run.stage_timings ?? []).map((t) => [t.stage, t.ms]));
  const maxMs = Math.max(1, ...Array.from(timings.values()));

  return (
    <div>
      <Link href="/runs" style={{ fontSize: "0.85rem" }}>
        ← Runs
      </Link>
      <header style={{ margin: "12px 0 20px", display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 8 }}>
        <h1>Run trace</h1>
        <span className={`chip ${run.status === "succeeded" ? "chip--cleared" : run.status === "failed" ? "chip--blocked" : "chip--unknown"}`}>
          {run.status}
          {LIVE.has(run.status) ? " · live" : ""}
        </span>
      </header>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="mono muted" style={{ fontSize: "0.82rem" }}>
          started {shortDate(run.started_at)} · finished {shortDate(run.finished_at)}
        </div>
        <div className="mono" style={{ marginTop: 10, display: "flex", gap: 20, flexWrap: "wrap" }}>
          <span>found {run.found ?? 0}</span>
          <span>cleared {run.cleared ?? 0}</span>
          <span>blocked {run.blocked ?? 0}</span>
          <span>{run.tool_calls ?? 0} tool calls</span>
        </div>
      </div>

      <h3 style={{ marginBottom: 12 }}>Flow stages</h3>
      <div className="grid">
        {STAGES.map((s) => {
          const ms = timings.get(s);
          const done = ms !== undefined;
          return (
            <div className="card" key={s} style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span className="mono" style={{ width: 90 }}>
                {s}
              </span>
              <div style={{ flex: 1, height: 10, background: "var(--rule)", borderRadius: 5, overflow: "hidden" }}>
                <div style={{ width: done ? `${(ms! / maxMs) * 100}%` : "0%", height: "100%", background: "var(--cleared)" }} />
              </div>
              <span className="mono muted" style={{ width: 90, textAlign: "right", fontSize: "0.82rem" }}>
                {done ? `${ms!.toFixed(0)} ms` : LIVE.has(run.status) ? "…" : "—"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
