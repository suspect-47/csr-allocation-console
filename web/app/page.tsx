"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import AllocationBar from "@/components/AllocationBar";
import { SkeletonBar, SkeletonCard } from "@/components/Skeleton";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import type { ConsoleData } from "@/lib/types";

type RunState = "idle" | "running" | "error";

export default function ConsolePage() {
  const [data, setData] = useState<ConsoleData | null>(null);
  const [values, setValues] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [runState, setRunState] = useState<RunState>("idle");
  const [runNote, setRunNote] = useState("");
  const [committed, setCommitted] = useState(false);
  const [commitError, setCommitError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const d = await api.getConsole();
    setData(d);
    setValues(d.cards.map((c) => c.amount ?? 0));
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const triggerRun = useCallback(async () => {
    setRunState("running");
    setRunNote("Enqueued. Scouting and verifying…");
    try {
      const { run_id } = await api.triggerRun();
      for (;;) {
        await new Promise((r) => setTimeout(r, 2000));
        const run = await api.getRun(run_id);
        setRunNote(`Run ${run.status} · found ${run.found ?? 0} · cleared ${run.cleared ?? 0}`);
        if (run.status === "succeeded") break;
        if (run.status === "failed") {
          setRunState("error");
          setRunNote("Run failed — see the run trace.");
          return;
        }
      }
      setRunState("idle");
      await load();
    } catch (e) {
      setRunState("error");
      setRunNote(String(e));
    }
  }, [load]);

  const commit = useCallback(async () => {
    if (!data) return;
    setCommitError("");
    try {
      await api.commit(data.cards.map((c, i) => ({ cause_id: c.id, amount: values[i] })));
      setCommitted(true);
    } catch (e) {
      setCommitError(String(e).replace(/^Error:\s*\d+\s*/, ""));
    }
  }, [data, values]);

  if (loading) {
    return (
      <>
        <SkeletonBar />
        <div className="grid cols-2" style={{ marginTop: 24 }}>
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </>
    );
  }
  if (!data) return null;

  if (!data.profile) {
    return (
      <div className="empty">
        <h3>No giving profile yet</h3>
        <p className="measure" style={{ margin: "0 auto 16px" }}>
          The console stays empty until a profile exists and a run has completed. Set your
          pillars, geography, and quarterly budget to begin.
        </p>
        <Link className="btn" href="/profile">
          Set up profile
        </Link>
      </div>
    );
  }

  if (data.cards.length === 0) {
    return (
      <div>
        <RunBanner state={runState} note={runNote} onRun={triggerRun} />
        <div className="empty">
          <h3>No causes cleared yet</h3>
          <p className="measure" style={{ margin: "0 auto 16px" }}>
            {data.has_run
              ? "The last run cleared nothing this quarter. Check the ledger for what did not clear, or run discovery again."
              : "Run discovery to find and verify emerging needs. Nothing is pre-loaded — every cause arrives with an evidence chain."}
          </p>
          {data.has_run && (
            <Link className="btn btn--ghost" href="/ledger">
              View ledger
            </Link>
          )}
        </div>
      </div>
    );
  }

  const budget = data.profile.quarterly_budget;
  const currency = data.profile.currency;

  return (
    <div>
      <RunBanner state={runState} note={runNote} onRun={triggerRun} />

      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 8 }}>
        <h1>Quarterly allocation</h1>
        <span className="mono muted">
          {money(budget, currency)} budget · {data.cards.length} cleared
        </span>
      </header>

      <AllocationBar
        cards={data.cards}
        values={values}
        budget={budget}
        currency={currency}
        onChange={(v) => {
          setValues(v);
          setCommitted(false);
        }}
      />

      <div style={{ display: "flex", gap: 12, alignItems: "center", margin: "8px 0 24px" }}>
        <button className="btn" onClick={commit} disabled={committed}>
          {committed ? "Allocation committed" : "Commit allocation"}
        </button>
        <span className="muted" style={{ fontSize: "0.85rem" }}>
          Produces a pledge sheet. No payment is made.
        </span>
        {commitError && (
          <span className="chip chip--blocked" role="alert">
            {commitError}
          </span>
        )}
      </div>

      <div className="grid cols-2">
        {data.cards.map((c, i) => (
          <article className="card" key={c.id}>
            <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
              <span className="chip chip--cleared">Cleared</span>
              {c.has_unknown && <span className="chip chip--unknown">1+ unknown</span>}
            </div>
            <h3>{c.headline}</h3>
            <p className="measure muted" style={{ fontSize: "0.95rem" }}>
              {c.summary}
            </p>
            <div className="mono muted" style={{ fontSize: "0.8rem", margin: "8px 0" }}>
              {c.pillar} · {c.geography} · {c.need_type}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span className="mono" style={{ fontWeight: 600 }}>
                {money(values[i], currency)}
              </span>
              <Link href={`/causes/${c.id}`} style={{ fontSize: "0.85rem" }}>
                Dossier →
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function RunBanner({ state, note, onRun }: { state: RunState; note: string; onRun: () => void }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 16 }}>
      <span className="mono muted" style={{ fontSize: "0.8rem" }} role="status">
        {note}
      </span>
      <button className="btn btn--ghost" onClick={onRun} disabled={state === "running"} aria-busy={state === "running"}>
        Run discovery
      </button>
    </div>
  );
}
