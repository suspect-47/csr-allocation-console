"use client";

import { useRef } from "react";
import { money } from "@/lib/format";
import type { ConsoleCard } from "@/lib/types";

const CAP = 0.4; // no single cause exceeds 40% of budget (spec §3.5)

function clamp(x: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, x));
}
function round2(xs: number[]): number[] {
  return xs.map((x) => Math.round(x * 100) / 100);
}

interface Props {
  cards: ConsoleCard[];
  values: number[];
  budget: number;
  currency: string;
  onChange: (values: number[]) => void;
}

// Drag a segment edge to rebalance; the adjacent segment compensates. The
// remainder is an open hatched region, never hidden, and never goes negative.
export default function AllocationBar({ cards, values, budget, currency, onChange }: Props) {
  const barRef = useRef<HTMLDivElement>(null);
  const cap = budget * CAP;
  const allocated = values.reduce((a, b) => a + b, 0);
  const remainder = Math.max(0, budget - allocated);
  const cum = (i: number) => values.slice(0, i + 1).reduce((a, b) => a + b, 0);

  function applyBoundary(i: number, target: number, start: number[], startRem: number): number[] {
    const next = [...start];
    if (i < values.length - 1) {
      const pool = start[i] + start[i + 1];
      const a = clamp(target, Math.max(0, pool - cap), Math.min(cap, pool));
      next[i] = a;
      next[i + 1] = pool - a;
    } else {
      const pool = start[i] + startRem;
      next[i] = clamp(target, 0, Math.min(cap, pool));
    }
    return round2(next);
  }

  function startDrag(i: number, e: React.PointerEvent) {
    e.preventDefault();
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    const startX = e.clientX;
    const width = barRef.current?.getBoundingClientRect().width ?? 1;
    const vpp = budget / width;
    const start = [...values];
    const startRem = remainder;
    const move = (ev: PointerEvent) => {
      const delta = (ev.clientX - startX) * vpp;
      onChange(applyBoundary(i, start[i] + delta, start, startRem));
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  function onKey(i: number, e: React.KeyboardEvent) {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    const step = budget * 0.01 * (e.key === "ArrowRight" ? 1 : -1);
    onChange(applyBoundary(i, values[i] + step, [...values], remainder));
  }

  if (!budget) return null;

  return (
    <div className="albar-wrap">
      <div className="albar" ref={barRef}>
        {values.map((v, i) => (
          <div
            key={cards[i].id}
            className={`albar-seg albar-seg--${cards[i].has_unknown ? "unknown" : "cleared"}`}
            style={{ width: `${(v / budget) * 100}%` }}
            title={`${cards[i].org_name} — ${money(v, currency)}`}
          >
            <span className="albar-label">
              {cards[i].org_name} · {money(v, currency)}
            </span>
          </div>
        ))}
        <div className="albar-remainder" style={{ width: `${(remainder / budget) * 100}%` }}>
          <span className="albar-label">Unallocated · {money(remainder, currency)}</span>
        </div>

        {values.map((_, i) => (
          <div
            key={`h-${cards[i].id}`}
            className="albar-handle"
            role="slider"
            tabIndex={0}
            aria-label={`Allocation for ${cards[i].org_name}`}
            aria-valuemin={0}
            aria-valuemax={Math.round(budget)}
            aria-valuenow={Math.round(values[i])}
            aria-valuetext={money(values[i], currency)}
            style={{ left: `${(cum(i) / budget) * 100}%` }}
            onPointerDown={(e) => startDrag(i, e)}
            onKeyDown={(e) => onKey(i, e)}
          />
        ))}
      </div>

      <div className="albar-legend" aria-hidden="true">
        <span><span className="swatch swatch--cleared" />Cleared</span>
        <span><span className="swatch swatch--unknown" />A check returned unknown</span>
        <span><span className="swatch swatch--remainder" />Unallocated</span>
      </div>
      <div className="albar-totals mono">
        <span>Allocated {money(allocated, currency)}</span>
        <span className="muted">Remainder {money(remainder, currency)}</span>
      </div>
    </div>
  );
}
