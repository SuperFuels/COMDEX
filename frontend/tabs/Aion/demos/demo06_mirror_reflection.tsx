"use client";

import React from "react";

export const demo06Meta = {
  id: "demo06-mirror",
  pillar: "PILLAR 6 • AWARENESS",
  title: "Mirror Container Recursive Reflection",
  testName: "MIRROR_REFLECTION",
  copy:
    "Self-modeling: the organism observes its own vitals (Φ / ADR / Θ) and emits commentary + an alignment score A. This is subject→object reflection, not just telemetry.",
} as const;

function fmt3(x: any) {
  const n = typeof x === "number" ? x : x != null ? Number(x) : NaN;
  return Number.isFinite(n) ? n.toFixed(3) : "—";
}

export function Demo06MirrorPanel(props: { mirror: any | null }) {
  const st = props.mirror?.state ?? props.mirror ?? {};
  const A = st.A ?? st.alignment ?? null;
  const line = st.commentary ?? st.narration ?? st.last_line ?? null;
  const log: string[] = Array.isArray(st.log) ? st.log : Array.isArray(st.lines) ? st.lines : [];

  return (
    <div className="w-full rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-500">
            Mirror Reflection Log
          </div>
          <div className="mt-2 text-2xl font-black uppercase italic tracking-tight text-white">
            A = {fmt3(A)}
          </div>
          <div className="mt-3 text-sm font-medium text-slate-400 max-w-xl">
            {line ? String(line) : "Awaiting mirror feed… (wire /api/mirror to real Φ/ADR/Θ + commentary output)"}
          </div>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/3 px-4 py-3">
          <div className="font-mono text-[10px] uppercase tracking-widest text-slate-500">Mode</div>
          <div className="mt-1 font-mono text-[11px] uppercase tracking-widest text-slate-200">
            SELF_OBSERVE
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Metric k="ADR Zone" v={String(st.adr_zone ?? st.zone ?? "—")} />
        <Metric k="RSI" v={fmt3(st.rsi)} />
        <Metric k="Θ age_ms" v={st.hb_age_ms != null ? String(st.hb_age_ms) : "—"} mono />
        <Metric k="Φ_coh" v={fmt3(st.phi_coherence)} />
      </div>

      <div className="mt-6 rounded-xl border border-white/10 bg-[#0b1224] p-4">
        <div className="font-mono text-[10px] uppercase tracking-widest text-slate-500">Thought Stream</div>
        <div className="mt-3 max-h-[220px] overflow-auto space-y-2 font-mono text-[11px] leading-relaxed text-slate-300">
          {log.length ? (
            log.slice(-12).map((l, i) => <div key={i}>{l}</div>)
          ) : (
            <div className="text-slate-500">No lines yet.</div>
          )}
        </div>
      </div>

      <div className="mt-6 border-t border-white/5 pt-4 font-mono text-[10px] uppercase tracking-widest text-slate-600">
        Proof-of-life: “the system comments on its own state” + A converges as stability returns.
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