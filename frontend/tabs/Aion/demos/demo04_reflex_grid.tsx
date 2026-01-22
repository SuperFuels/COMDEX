// frontend/tabs/Aion/demos/demo04_reflex_grid.tsx
"use client";

import React, { useMemo } from "react";
import { Card, StatRow, MiniBar, Button, clamp01, classNames } from "./ui";

// ✅ add import (your earlier snippet)
import QFCViewport from "@/src/glyphnet/components/QFCViewport";

export const demo04Meta = {
  id: "reflex",
  pillar: "Pillar: Environmental Response",
  title: "Demo Container 04 — Reflex (Cognitive Grid)",
  testName: "Cognitive Grid Curiosity-Drift",
  copy:
    "This is AION’s reflex layer. The agent moves toward novelty (inverse visit frequency). When it hits a danger node, it triggers an immediate Φ-entropy spike and emits the linguistic reflex: “Stability breached.” That is the pain-response primitive: an internal state change + a self-report, without operator prompting.",
} as const;

export type ReflexState = {
  ok?: boolean;
  grid_size?: number;
  vision_range?: number;
  max_steps?: number;
  age_ms?: number;
  now_s?: number;
  timestamp?: number;
  position?: { x: number; y: number };
  visited?: Record<string, number>;
  collected?: string[];
  alive?: boolean;
  steps?: number;
  score?: number;
  last_outcome?: string;
  last_reflection?: string;
  last_event_type?: string; // move | collect | symbol | danger
  last_tile?: string;
  stability_breached?: boolean;
  metrics?: { novelty?: number; coherence?: number; entropy?: number };
  world?: Record<string, string>; // "x,y" -> token
  events?: Array<{ ts: number; type: string; tile: string; token?: string; reflection: string }>;
};

export type ReflexEnvelope = {
  ok: boolean;
  data_root: string;
  source_file?: string | null;
  age_ms?: number | null;
  now_s?: number;
  state?: ReflexState | null;
};

export function Demo04ReflexGridPanel(props: {
  reflex: ReflexEnvelope | null;
  actionBusy: string | null;
  onReset: () => Promise<void>;
  onStep: () => Promise<void>;
  onRun: () => Promise<void>;
}) {
  const { reflex, actionBusy, onReset, onStep, onRun } = props;
  const st = reflex?.state || null;

  const metrics = st?.metrics || {};
  const novelty = typeof metrics.novelty === "number" ? metrics.novelty : 0;
  const coherence = typeof metrics.coherence === "number" ? metrics.coherence : 0;
  const entropy = typeof metrics.entropy === "number" ? metrics.entropy : 0;

  const alive = st?.alive !== false;
  const evType = st?.last_event_type || "—";
  const danger = evType === "danger" || st?.stability_breached;

  const interpretation = useMemo(() => {
    if (!st) return { label: "OFFLINE", tone: "text-rose-300", desc: "No reflex state detected from backend." };
    if (danger) return { label: "PAIN REFLEX", tone: "text-rose-300", desc: "Danger contact: entropy spike + “Stability breached.”" };
    return { label: "CURIOSITY SEEKING", tone: "text-emerald-200", desc: "Novelty gradient is driving movement." };
  }, [st, danger]);

  // ✅ feed reflex state into the QFC scene via a lightweight frame extension
  const qfcFrame = useMemo(() => {
    return {
      t: Date.now(),
      mode: "reflex_grid",
      reflex: st, // <— QFCDemoReflexGrid reads this
    } as any;
  }, [st]);

  return (
    <Card
      title="Cognitive Grid — Curiosity + Danger Reflex"
      subtitle="GET /api/reflex • POST /api/demo/reflex/{reset,step,run}"
      right={
        <div
          className={classNames(
            "rounded-full px-3 py-1 text-xs",
            danger ? "bg-rose-500/20 text-rose-200" : "bg-emerald-500/15 text-emerald-200"
          )}
        >
          {danger ? "Stability breached" : "Exploring"}
        </div>
      }
    >
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {/* LEFT: QFC canvas */}
        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold text-white">Grid (live)</div>
            <div className={classNames("text-xs font-semibold", interpretation.tone)}>{interpretation.label}</div>
          </div>

          {/* ✅ QFC canvas render */}
          <div className="h-[340px] w-full">
            <QFCViewport
              title="Reflex Grid — Live"
              subtitle="Cognitive Grid Curiosity-Drift"
              domainLabel="BIO"
              mode={"reflex_grid" as any}
              frame={qfcFrame}
              showDataPanel={false}
            />
          </div>

          {/* keep your buttons */}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Button tone="neutral" disabled={actionBusy !== null} onClick={onReset} title="POST /api/demo/reflex/reset">
              {actionBusy === "reflex_reset" ? "Resetting…" : "Reset world"}
            </Button>
            <Button tone="primary" disabled={actionBusy !== null || !alive} onClick={onStep} title="POST /api/demo/reflex/step">
              {actionBusy === "reflex_step" ? "Stepping…" : "Step once"}
            </Button>
            <Button tone="primary" disabled={actionBusy !== null || !alive} onClick={onRun} title="POST /api/demo/reflex/run">
              {actionBusy === "reflex_run" ? "Running…" : "Run (60s)"}
            </Button>
          </div>
        </div>

        {/* RIGHT: metrics + proof (unchanged) */}
        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="mb-2 text-sm font-semibold text-white">Reflex Bio-metrics</div>

          <div className="divide-y divide-white/10">
            <StatRow label="age_ms" hint="freshness proof" value={reflex?.age_ms != null ? `${reflex.age_ms} ms` : "—"} />
            <StatRow label="position" hint="agent coordinates" value={<span className="font-mono">{st?.position?.x ?? 0},{st?.position?.y ?? 0}</span>} />
            <StatRow label="steps" hint="time in environment" value={<span className="font-mono">{st?.steps ?? "—"}</span>} />
            <StatRow label="event" hint="last reflex trigger" value={<span className="font-mono">{evType}</span>} />
          </div>

          <div className="mt-4">
            <div className="text-xs text-white/50 mb-2">Novelty</div>
            <MiniBar value={clamp01(novelty)} goodMin={0.65} warnMin={0.25} />
            <div className="mt-3 text-xs text-white/50 mb-2">Coherence</div>
            <MiniBar value={clamp01(coherence)} goodMin={0.85} warnMin={0.5} />
            <div className="mt-3 text-xs text-white/50 mb-2">Entropy</div>
            <MiniBar value={clamp01(entropy)} goodMin={0.25} warnMin={0.6} />
          </div>

          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3">
            <div className="text-xs font-medium uppercase tracking-wider text-white/60">Proof (self-report)</div>
            <p className="mt-2 text-sm leading-6 text-white/80">
              {st?.last_reflection || interpretation.desc}
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
}