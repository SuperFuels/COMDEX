// frontend/tabs/Aion/demos/demo02_immune_adr.tsx
"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { Card, StatRow, MiniBar, Button, clamp01, classNames, fmt2, fmt3 } from "./ui";

export type AdrStreamEvent = {
  timestamp?: number;
  stability?: number; // used as RSI in your current emitters
  RSI?: number;
  drift_entropy?: number;
  entropy?: number;
  source?: string;
};

export type DriftRepairEvent = {
  timestamp?: number;
  event?: string;
  source?: string;
  rsi?: number;
  drift_entropy?: number;
  pre?: { epsilon?: number; k?: number; memory_weight?: number };
  post?: { epsilon?: number; k?: number; memory_weight?: number };
};

export type PalState = {
  epsilon?: number;
  k?: number;
  memory_weight?: number;
  timestamp?: number;
  reason?: string;
};

export type AdrBundle = {
  stream?: AdrStreamEvent | null;
  lastRepair?: DriftRepairEvent | null;
  palState?: PalState | null;
};

// small local hook (demo-local effect)
function usePulse(ms = 750) {
  const [on, setOn] = useState(false);
  const tRef = useRef<any>(null);

  const pulse = () => {
    setOn(true);
    if (tRef.current) clearTimeout(tRef.current);
    tRef.current = setTimeout(() => setOn(false), ms);
  };

  useEffect(() => () => tRef.current && clearTimeout(tRef.current), []);
  return { on, pulse };
}

// --- Demo 02 exports ---
export const demo02Meta = {
  id: "immune",
  pillar: "Pillar: Self-Healing",
  title: "Demo Container 02 — Immune Response",
  testName: "Adaptive Drift Repair (ADR) Activation",
  copy:
    "This is AION’s immune system. We can force instability by injecting drift into the resonance stream. When the Resonance Stability Index (RSI) drops below 0.60, AION does not wait for an operator — it triggers Adaptive Drift Repair (ADR). You’ll see a red pulse at the exact moment the organism detects damage, followed by an autonomous reset of its own tuning parameters (ε and k) to regain stability. That’s self-healing, not monitoring.",
} as const;

export function Demo02AdrPanel(props: {
  adr: AdrBundle | null;
  actionBusy: string | null;
  onInject: () => Promise<void>;
  onRun: () => Promise<void>;
}) {
  const { adr, actionBusy, onInject, onRun } = props;

  // ---- derived ADR state ----
  const rsi = useMemo(() => {
    const s = adr?.stream;
    const v = s?.RSI ?? s?.stability;
    return typeof v === "number" ? v : 1.0;
  }, [adr]);

  const driftEntropy = useMemo(() => {
    const s = adr?.stream;
    const v = s?.drift_entropy ?? s?.entropy;
    return typeof v === "number" ? v : 0.0;
  }, [adr]);

  const adrStatus = useMemo(() => {
    if (rsi < 0.6) return "Triggered";
    if (rsi < 0.95) return "Armed";
    return "Stable";
  }, [rsi]);

  const adrTone =
    adrStatus === "Triggered" ? "text-rose-300" : adrStatus === "Armed" ? "text-amber-200" : "text-emerald-200";

  // red pulse when lastRepair timestamp changes
  const { on: redPulseOn, pulse: fireRedPulse } = usePulse(750);
  const lastRepairTsRef = useRef<number | null>(null);

  useEffect(() => {
    const ts = adr?.lastRepair?.timestamp ?? null;
    if (ts && ts !== lastRepairTsRef.current) {
      lastRepairTsRef.current = ts;
      fireRedPulse();
    }
  }, [adr?.lastRepair?.timestamp, fireRedPulse]);

  return (
    <Card
      title="Adaptive Drift Repair (ADR) Activation"
      subtitle="GET /api/adr • sources: resonance_stream.jsonl + drift_repair.log + pal_state.json"
      right={
        <div className={classNames("rounded-full px-3 py-1 text-xs", redPulseOn ? "bg-rose-500 text-white" : "bg-white/10 text-white/70")}>
          {redPulseOn ? "Red Pulse" : "Pulse"}
        </div>
      }
    >
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {/* Left: RSI + Stream */}
        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="mb-2 flex items-center justify-between">
            <div className="text-sm font-semibold text-white">RSI Stability Bar</div>
            <div className={classNames("text-sm font-semibold", adrTone)}>{adrStatus}</div>
          </div>

          <MiniBar value={clamp01(rsi)} goodMin={0.95} warnMin={0.6} />

          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-white/50">drift_entropy</div>
              <div className="mt-1 font-mono text-sm text-white">{fmt2(driftEntropy)}</div>
            </div>
            <div>
              <div className="text-xs text-white/50">source</div>
              <div className="mt-1 font-mono text-sm text-white">{adr?.stream?.source || "—"}</div>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Button tone="neutral" disabled={actionBusy !== null} onClick={onInject} title="POST /api/demo/adr/inject">
              {actionBusy === "adr_inject" ? "Injecting…" : "Inject drift"}
            </Button>
            <Button tone="primary" disabled={actionBusy !== null} onClick={onRun} title="POST /api/demo/adr/run">
              {actionBusy === "adr_run" ? "Running…" : "Run ADR"}
            </Button>
          </div>
        </div>

        {/* Right: Repair + PAL */}
        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="mb-2 text-sm font-semibold text-white">Immune Action Panel</div>

          <div className="divide-y divide-white/10">
            <StatRow
              label="Latest ADR trigger"
              hint="drift_repair.log"
              value={adr?.lastRepair?.timestamp ? new Date((adr.lastRepair.timestamp as number) * 1000).toLocaleString() : "—"}
            />
            <StatRow label="ε (exploration)" hint="pal_state.json" value={<span className="font-mono">{fmt3(adr?.palState?.epsilon ?? null)}</span>} />
            <StatRow label="k (k-NN depth)" hint="pal_state.json" value={<span className="font-mono">{adr?.palState?.k ?? "—"}</span>} />
            <StatRow label="memory_weight" hint="pal_state.json" value={<span className="font-mono">{fmt3(adr?.palState?.memory_weight ?? null)}</span>} />
          </div>

          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3">
            <div className="text-xs font-medium uppercase tracking-wider text-white/60">Proof (before → after)</div>
            <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-xs text-white/50">ε</div>
                <div className="mt-1 font-mono text-white">
                  {fmt3(adr?.lastRepair?.pre?.epsilon ?? null)} → {fmt3(adr?.lastRepair?.post?.epsilon ?? null)}
                </div>
              </div>
              <div>
                <div className="text-xs text-white/50">k</div>
                <div className="mt-1 font-mono text-white">
                  {adr?.lastRepair?.pre?.k ?? "—"} → {adr?.lastRepair?.post?.k ?? "—"}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}