"use client";

import React from "react";
import { Button, Card, MiniBar, StatRow, clamp01, classNames, fmt2, safeDateAgeMs } from "./ui";

export type PhiState = {
  "Φ_load"?: number;
  "Φ_flux"?: number;
  "Φ_entropy"?: number;
  "Φ_coherence"?: number;
  beliefs?: {
    stability?: number;
    curiosity?: number;
    trust?: number;
    clarity?: number;
  };
  last_update?: string | null;
};

// --- Demo 01 exports ---
export const demo01Meta = {
  id: "metabolism",
  pillar: "Pillar: Energy Processing",
  title: "Demo Container 01 — Metabolic Core",
  testName: "Φ-Vector Flux Monitoring",
  copy:
    "This is AION’s metabolic core. Every thought leaves a signature in a Φ-field: coherence (structure), entropy (heat), flux (activity), and load (strain). AION continuously updates its baseline from its own memory stream, meaning cognition has a measurable internal cost. If entropy rises, the organism destabilizes; if coherence recovers, it reinforces a stable internal state. This is not a static dashboard — it’s a living regulation loop.",
} as const;

export function Demo01MetabolismPanel(props: {
  phi: PhiState | null;
  actionBusy: string | null;
  onReset: () => Promise<void>;
  onInjectEntropy: () => Promise<void>;
  onRecover: () => Promise<void>;
}) {
  const { phi, actionBusy, onReset, onInjectEntropy, onRecover } = props;

  const lastUpdateAge = safeDateAgeMs(phi?.last_update);
  const metabolicActive = lastUpdateAge !== null && lastUpdateAge <= 2000;

  return (
    <Card
      title="Φ-Vector Flux Monitoring (Metabolism)"
      subtitle="GET /api/phi • source: phi_reinforce_state.json (written by phi_reinforce.py)"
      right={
        <div
          className={classNames(
            "rounded-full px-3 py-1 text-xs",
            metabolicActive ? "bg-emerald-500/15 text-emerald-200" : "bg-white/10 text-white/70"
          )}
        >
          {metabolicActive ? "Metabolic Pulse: ACTIVE" : "At Rest"}
        </div>
      }
    >
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="mb-2 text-sm font-semibold text-white">Vitals (Φ 4-vector)</div>
          <div className="divide-y divide-white/10">
            <StatRow label="Φ_load" hint="Cognitive Strain" value={fmt2(phi?.["Φ_load"])} />
            <StatRow label="Φ_flux" hint="Processing Flow" value={fmt2(phi?.["Φ_flux"])} />
            <StatRow label="Φ_entropy" hint="Heat / Disorder" value={fmt2(phi?.["Φ_entropy"])} />
            <StatRow label="Φ_coherence" hint="Structure / Order" value={fmt2(phi?.["Φ_coherence"])} />
          </div>
        </div>

        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="mb-2 text-sm font-semibold text-white">Belief / Mood Vector (0–1)</div>
          <div className="space-y-3">
            <MiniBar value={clamp01(phi?.beliefs?.stability ?? 0.5)} label={`stability • ${fmt2(phi?.beliefs?.stability ?? null)}`} />
            <MiniBar value={clamp01(phi?.beliefs?.curiosity ?? 0.5)} label={`curiosity • ${fmt2(phi?.beliefs?.curiosity ?? null)}`} />
            <MiniBar value={clamp01(phi?.beliefs?.trust ?? 0.5)} label={`trust • ${fmt2(phi?.beliefs?.trust ?? null)}`} />
            <MiniBar value={clamp01(phi?.beliefs?.clarity ?? 0.5)} label={`clarity • ${fmt2(phi?.beliefs?.clarity ?? null)}`} />
          </div>

          <div className="mt-4 text-xs text-white/50">
            last_update: <span className="font-mono">{phi?.last_update || "—"}</span>
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <Button tone="neutral" disabled={actionBusy !== null} onClick={onReset} title="POST /api/demo/phi/reset">
          {actionBusy === "reset" ? "Resetting…" : "Reset baseline"}
        </Button>

        <Button tone="danger" disabled={actionBusy !== null} onClick={onInjectEntropy} title="POST /api/demo/phi/inject_entropy">
          {actionBusy === "inject" ? "Injecting…" : "Inject entropy"}
        </Button>

        <Button tone="primary" disabled={actionBusy !== null} onClick={onRecover} title="POST /api/demo/phi/recover">
          {actionBusy === "recover" ? "Recovering…" : "Recover"}
        </Button>
      </div>
    </Card>
  );
}