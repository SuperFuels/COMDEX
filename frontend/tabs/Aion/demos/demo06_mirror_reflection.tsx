// frontend/tabs/Aion/demos/demo06_mirror_reflection.tsx
"use client";

import React, { useMemo } from "react";

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

function fmt0(x: any) {
  const n = typeof x === "number" ? x : x != null ? Number(x) : NaN;
  return Number.isFinite(n) ? String(Math.round(n)) : "—";
}

function deriveAdrZone(rsi: any) {
  const n = typeof rsi === "number" ? rsi : rsi != null ? Number(rsi) : NaN;
  if (!Number.isFinite(n)) return "—";
  if (n >= 0.95) return "GREEN";
  if (n >= 0.6) return "YELLOW";
  return "RED";
}

export function Demo06MirrorPanel(props: { mirror: any | null }) {
  // backend shape currently:
  // GET /api/mirror -> { ok, state: { demo, session_id, frames:[{A, phi{Φ_coherence, Φ_entropy,...}, heartbeat_age_ms, narration}], A_final } }
  const root = props.mirror ?? null;
  const st = root?.state ?? root ?? null;

  const view = useMemo(() => {
    const frames = Array.isArray(st?.frames) ? st.frames : Array.isArray(st?.state?.frames) ? st.state.frames : [];
    const lastFrame = frames.length ? frames[frames.length - 1] : null;

    const A =
      st?.A ??
      st?.alignment ??
      st?.A_final ??
      lastFrame?.A ??
      lastFrame?.alignment ??
      null;

    // pull phi + theta age from frame if present
    const phi = lastFrame?.phi ?? st?.phi ?? st?.state?.phi ?? null;

    const phiCoh =
      phi?.["Φ_coherence"] ??
      phi?.Phi_coherence ??
      phi?.phi_coherence ??
      st?.phi_coherence ??
      st?.Phi_coherence ??
      null;

    const thetaAgeMs =
      lastFrame?.heartbeat_age_ms ??
      lastFrame?.hb_age_ms ??
      st?.heartbeat_age_ms ??
      st?.hb_age_ms ??
      null;

    // RSI/zone may come from ADR feed, but mirror currently doesn’t carry it.
    // If you later add it, this will auto-render.
    const rsi =
      st?.rsi ??
      st?.RSI ??
      st?.adr?.rsi ??
      st?.derived?.rsi ??
      null;

    const zone =
      st?.adr_zone ??
      st?.zone ??
      st?.adr?.zone ??
      st?.derived?.zone ??
      deriveAdrZone(rsi);

    // commentary lines
    const lastLine =
      st?.commentary ??
      st?.narration ??
      st?.last_line ??
      lastFrame?.narration ??
      lastFrame?.commentary ??
      null;

    // build a small thought stream from frame narrations (or existing log/lines)
    const explicitLog: string[] = Array.isArray(st?.log)
      ? st.log
      : Array.isArray(st?.lines)
      ? st.lines
      : [];

    const frameLog: string[] = frames
      .map((f: any) => f?.narration ?? f?.commentary ?? null)
      .filter(Boolean)
      .map(String);

    const log = explicitLog.length ? explicitLog : frameLog;

    return { frames, lastFrame, A, lastLine, log, rsi, zone, thetaAgeMs, phiCoh };
  }, [st]);

  return (
    <div className="w-full rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-500">
            Mirror Reflection Log
          </div>
          <div className="mt-2 text-2xl font-black uppercase italic tracking-tight text-slate-900">
            A = {fmt3(view.A)}
          </div>
          <div className="mt-3 text-sm font-medium text-slate-600 max-w-xl">
            {view.lastLine
              ? String(view.lastLine)
              : "Awaiting mirror feed… (run /api/demo/mirror/run or wire mirror to continuous commentary)"}{" "}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <div className="font-mono text-[10px] uppercase tracking-widest text-slate-500">Mode</div>
          <div className="mt-1 font-mono text-[11px] uppercase tracking-widest text-slate-800">
            SELF_OBSERVE
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Metric k="ADR Zone" v={String(view.zone ?? "—")} />
        <Metric k="RSI" v={fmt3(view.rsi)} />
        <Metric k="Θ age_ms" v={view.thetaAgeMs != null ? fmt0(view.thetaAgeMs) : "—"} mono />
        <Metric k="Φ_coh" v={fmt3(view.phiCoh)} />
      </div>

      <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="font-mono text-[10px] uppercase tracking-widest text-slate-500">Thought Stream</div>
        <div className="mt-3 max-h-[220px] overflow-auto space-y-2 font-mono text-[11px] leading-relaxed text-slate-700">
          {view.log.length ? (
            view.log.slice(-12).map((l, i) => <div key={i}>{l}</div>)
          ) : (
            <div className="text-slate-500">No lines yet.</div>
          )}
        </div>
      </div>

      <div className="mt-6 border-t border-slate-200 pt-4 font-mono text-[10px] uppercase tracking-widest text-slate-500">
        Proof-of-life: “the system comments on its own state” + A converges as stability returns.
      </div>
    </div>
  );
}

function Metric(props: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="font-mono text-[10px] uppercase tracking-widest text-slate-500">{props.k}</div>
      <div className={`mt-2 text-lg font-bold text-slate-900 ${props.mono ? "font-mono text-[12px]" : ""}`}>
        {props.v}
      </div>
    </div>
  );
}