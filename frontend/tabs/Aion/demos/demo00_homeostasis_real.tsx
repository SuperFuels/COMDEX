"use client";

import React, { useMemo } from "react";

export const demo00Meta = {
  id: "demo00-homeostasis",
  pillar: "PILLAR 1 • INTEGRITY",
  title: "Resonant Equilibrium Auto-Lock (REAL)",
  testName: "REAL_AUTO_LOCK",
  copy:
    "Self-preservation gate. AION emits sqi_checkpoint, probes ⟲ equilibrium, and locks when ⟲ ≥ threshold. This is phase-closure without operator instruction.",
} as const;

function fmt3(x: any) {
  const n = typeof x === "number" ? x : x != null ? Number(x) : NaN;
  return Number.isFinite(n) ? n.toFixed(3) : "—";
}

function Chip({ tone, label }: { tone: "good" | "warn" | "bad" | "neutral"; label: string }) {
  const cls =
    tone === "good"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
      : tone === "warn"
      ? "border-amber-500/30 bg-amber-500/10 text-amber-200"
      : tone === "bad"
      ? "border-rose-500/30 bg-rose-500/10 text-rose-200"
      : "border-white/10 bg-white/5 text-slate-200";
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 font-mono text-[10px] font-bold tracking-[0.2em] uppercase ${cls}`}>
      {label}
    </span>
  );
}

export function Demo00HomeostasisPanel(props: { homeostasis: any | null }) {
  const st = props.homeostasis?.homeostasis?.last ?? props.homeostasis?.last ?? props.homeostasis?.state ?? null;

  const locked = typeof st?.locked === "boolean" ? st.locked : null;
  const tone = locked === true ? "good" : locked === false ? "warn" : "neutral";
  const label = locked === true ? "LOCKED" : locked === false ? "UNLOCKED" : "NO_FEED";

  const eq = st?.["⟲"] ?? st?.eq;
  const dphi = st?.["ΔΦ"] ?? st?.dphi;
  const sqi = st?.SQI ?? st?.["SQI"];
  const rho = st?.["ρ"] ?? st?.rho;
  const Ibar = st?.["Ī"] ?? st?.Ibar;
  const thr = st?.threshold ?? st?.["threshold"] ?? 0.975;
  const lockId = st?.lock_id ?? st?.["lock_id"];

  const note = useMemo(() => {
    if (locked === true) return "Gate closed: equilibrium held above threshold.";
    if (locked === false) return "Gate open: equilibrium not yet above threshold.";
    return "Awaiting homeostasis feed (run your REAL producer / aggregator).";
  }, [locked]);

  return (
    <div className="w-full rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-500">
            Phase Closure Monitor
          </div>
          <div className="mt-2 text-2xl font-black uppercase italic tracking-tight text-white">
            ⟲ ≥ {String(thr)}
          </div>
          <div className="mt-3 text-sm font-medium text-slate-400 max-w-xl">
            {note}
          </div>
        </div>
        <Chip tone={tone as any} label={label} />
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Metric k="⟲" v={fmt3(eq)} />
        <Metric k="ΔΦ" v={fmt3(dphi)} />
        <Metric k="SQI" v={fmt3(sqi)} />
        <Metric k="ρ" v={fmt3(rho)} />
        <Metric k="Ī" v={fmt3(Ibar)} />
        <Metric k="lock_id" v={lockId ? String(lockId) : "—"} mono />
      </div>

      <div className="mt-6 border-t border-white/5 pt-4 font-mono text-[10px] uppercase tracking-widest text-slate-600">
        Proof-of-life: stability is detected internally, then promoted to a lockable state.
      </div>
    </div>
  );
}

function Metric(props: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/3 p-4">
      <div className="font-mono text-[10px] uppercase tracking-widest text-slate-500">{props.k}</div>
      <div className={`mt-2 text-lg font-bold text-white ${props.mono ? "font-mono text-[12px]" : ""}`}>{props.v}</div>
    </div>
  );
}