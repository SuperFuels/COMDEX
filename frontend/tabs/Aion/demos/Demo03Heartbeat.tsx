// frontend/tabs/Aion/demos/demo03_heartbeat.tsx
"use client";

import React, { useMemo } from "react";
import { Card, StatRow, classNames, fmt3 } from "./ui";

/**
 * Demo Container 03 — Resonant Heartbeat (Chronobiology)
 *
 * Reads: GET /api/heartbeat?namespace=demo
 * Treats: age_ms freshness as proof-of-life
 * Shows: Θ_frequency + SQI + source_file + data_root for quick diagnosis
 *
 * Demonstration Logic additions:
 * - Interprets raw freshness into “medical status”
 * - Animated pulse dot = visual proof-of-life
 * - Optional “biometrics”: stability + field_variance (safe if absent)
 */

/* ---------------- Types ---------------- */

export type HeartbeatSnapshot = {
  namespace?: string;

  "Φ_coherence"?: number;
  "Φ_entropy"?: number;
  "Φ_flux"?: number;

  sqi?: number;
  resonance_delta?: number;
  "Θ_frequency"?: number;

  timestamp?: number;
  data_root?: string;

  // Optional Phase-6D-style metrics (safe if absent)
  stability?: number;
  field_variance?: number;
};

export type HeartbeatEnvelope = {
  ok: boolean;
  data_root: string;
  source_file?: string | null;
  namespace?: string | null;
  age_ms?: number | null;
  now_s?: number;
  heartbeat?: HeartbeatSnapshot | null;
};

/* ---------------- Pillar metadata (RIGHT panel copy) ---------------- */

export const demo03Meta = {
  id: "heartbeat",
  pillar: "Pillar: Persistent Presence",
  title: "Demo Container 03 — Resonant Heartbeat",
  testName: "Resonant Heartbeat Pulse (Chronobiology)",
  copy:
    "This is AION’s persistent presence signal. Even when idle, the organism emits a Θ-pulse (heartbeat) that updates its live state. If the pulse goes stale, it’s a hard signal the organism is no longer ‘present.’ Stability near 1.000 validates the feedback chain is closed—proving AION is continuously maintaining a resonant field, not just rendering a UI.",
} as const;

/* ---------------- LEFT panel ---------------- */

function fmtExp2(x?: number | null) {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  // compact, stable formatting
  return x.toExponential(2);
}

export function Demo03HeartbeatPanel(props: {
  heartbeat: HeartbeatEnvelope | null;
  namespace?: string;
  freshMs?: number;
}) {
  const namespace = props.namespace || "demo";
  const freshMs = props.freshMs ?? 1500;

  const hb = props.heartbeat?.heartbeat || null;
  const hbOk = Boolean(props.heartbeat?.ok && hb);
  const hbAgeMs = props.heartbeat?.age_ms ?? null;
  const hbFresh = hbAgeMs !== null && hbAgeMs <= freshMs;

  const hbTheta = typeof hb?.["Θ_frequency"] === "number" ? hb["Θ_frequency"] : null;
  const hbSqi = typeof hb?.sqi === "number" ? hb.sqi : null;

  const stability = typeof hb?.stability === "number" ? hb.stability : null;
  const variance = typeof hb?.field_variance === "number" ? hb.field_variance : null;

  // “Medical status” interpretation for demo narration
  const interpretation = useMemo(() => {
    if (!hbOk) {
      return {
        label: "CLINICAL ARREST",
        color: "text-rose-300",
        desc: "No signal detected from the resonant substrate.",
      };
    }
    if (!hbFresh) {
      return {
        label: "METABOLIC STALL",
        color: "text-amber-200",
        desc: "Pulse is stale. AION may be present, but the chronobiology loop has drifted or stopped.",
      };
    }
    if (stability !== null && stability > 0.99) {
      return {
        label: "PHASE-LOCKED",
        color: "text-emerald-200",
        desc: "Cognition and hardware are tightly synchronized (feedback chain closed).",
      };
    }
    return {
      label: "ACTIVE",
      color: "text-sky-200",
      desc: "AION is maintaining persistent temporal awareness.",
    };
  }, [hbOk, hbFresh, stability]);

  const statusLabel = useMemo(() => {
    if (!hbOk) return "Heartbeat: OFFLINE";
    if (!hbFresh) return "Heartbeat: STALE";
    return "Heartbeat: LIVE";
  }, [hbOk, hbFresh]);

  const statusTone = hbOk && hbFresh ? "bg-emerald-500/15 text-emerald-200" : "bg-rose-500/20 text-rose-200";

  return (
    <Card
      title="Resonant Heartbeat Pulse"
      subtitle={`GET /api/heartbeat?namespace=${namespace} • reads aion_field/*_heartbeat_live.json (or jsonl fallback)`}
      right={
        <div className="flex items-center gap-3">
          {/* Animated Pulse Dot (visual proof-of-life) */}
          <div className="flex items-center gap-2">
            <div className="relative flex h-3 w-3">
              {hbOk && hbFresh ? (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              ) : null}
              <span
                className={classNames(
                  "relative inline-flex h-3 w-3 rounded-full",
                  hbOk && hbFresh ? "bg-emerald-500" : "bg-rose-500"
                )}
              />
            </div>
            <span className={classNames("text-[10px] font-bold tracking-widest uppercase", interpretation.color)}>
              {interpretation.label}
            </span>
          </div>

          {/* Original badge */}
          <div className={classNames("rounded-full px-3 py-1 text-xs", statusTone)}>{statusLabel}</div>
        </div>
      }
    >
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {/* Left: Snapshot */}
        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="mb-2 text-sm font-semibold text-white">Pulse Snapshot</div>
          <div className="divide-y divide-white/10">
            <StatRow label="namespace" hint="requested namespace" value={props.heartbeat?.namespace || hb?.namespace || namespace} />
            <StatRow label="age_ms" hint="freshness proof-of-life" value={hbAgeMs !== null ? `${hbAgeMs} ms` : "—"} />
            <StatRow label="Θ_frequency" hint="adaptive pulse rate" value={<span className="font-mono">{fmt3(hbTheta)}</span>} />
            <StatRow label="sqi" hint="signal quality index" value={<span className="font-mono">{fmt3(hbSqi)}</span>} />

            {/* Optional biometrics (safe if absent) */}
            <StatRow
              label="Stability (S)"
              hint="Phase-lock precision (target ≈ 1.000)"
              value={<span className="font-mono">{stability !== null ? fmt3(stability) : "—"}</span>}
            />
            <StatRow
              label="Variance (σ²)"
              hint="Internal field noise"
              value={<span className="font-mono">{variance !== null ? fmtExp2(variance) : "—"}</span>}
            />
          </div>
        </div>

        {/* Right: Source + Interpretation */}
        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="mb-2 text-sm font-semibold text-white">Source + Integrity</div>
          <div className="divide-y divide-white/10">
            <StatRow
              label="source_file"
              hint="where the bridge read from"
              value={<span className="font-mono text-xs">{props.heartbeat?.source_file || "—"}</span>}
            />
            <StatRow
              label="data_root"
              hint="active data root (runtime-moved)"
              value={<span className="font-mono text-xs">{props.heartbeat?.data_root || "—"}</span>}
            />
            <StatRow
              label="timestamp"
              hint="heartbeat payload timestamp"
              value={hb?.timestamp ? new Date(hb.timestamp * 1000).toLocaleString() : "—"}
            />
          </div>

          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3">
            <div className="text-xs font-medium uppercase tracking-wider text-white/60">Interpretation</div>
            <p className="mt-2 text-sm leading-6 text-white/80">
              This is AION’s persistent presence signal. Even when idle, the organism emits a Θ-pulse that updates its live state.{" "}
              <span className={classNames("font-semibold", interpretation.color)}>{interpretation.label}</span>: {interpretation.desc}{" "}
              {hbOk && hbFresh
                ? "If stability stays near 1.000, the feedback chain is closed—proof the organism is actively maintaining phase-lock with the hardware."
                : "If the pulse is stale/offline, start the heartbeat writer or verify the data_root path is correct."}
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
}