// frontend/tabs/Aion/demos/demo02_immune_adr.tsx
"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { Card, StatRow, MiniBar, Button, clamp01, classNames, fmt2, fmt3 } from "./ui";

/**
 * Backend now returns:
 * GET /api/adr =>
 * {
 *   latest_stream_event, latest_drift_repair, pal_state, derived:{rsi,zone,adr_status,red_pulse,...}
 * }
 *
 * And actions:
 * POST /api/adr/inject   { amount?: number, source?: string }
 * POST /api/adr/run      {}
 */

// ---------- Types matching backend (tolerant) ----------

export type AdrStreamEvent = {
  timestamp?: number; // new shape
  t?: number; // old shape
  stability?: number; // used as RSI in emitters
  RSI?: number;
  drift_entropy?: number;
  entropy?: number;
  source?: string;
  source_pair?: string;
};

export type DriftRepairEvent = {
  timestamp?: number;
  event?: string;
  type?: string;
  source?: string;
  rsi?: number;
  drift_entropy?: number;
  amount?: number;
  pre?: { epsilon?: number; k?: number; memory_weight?: number };
  post?: { epsilon?: number; k?: number; memory_weight?: number };
  before?: { epsilon?: number; k?: number; memory_weight?: number };
  after?: { epsilon?: number; k?: number; memory_weight?: number };
  pal_returncode?: number;
};

export type PalState = {
  epsilon?: number;
  k?: number;
  memory_weight?: number;
  timestamp?: number;
  ts?: number;
  reason?: string;
};

export type AdrDerived = {
  rsi?: number;
  zone?: "GREEN" | "YELLOW" | "RED" | "UNKNOWN";
  adr_status?: string; // "ARMED" | "TRIGGERED" | "RECOVERING" | ...
  red_pulse?: boolean;
  last_trigger_age_s?: number | null;
};

export type AdrApiResponse = {
  ok?: boolean;
  data_root?: string;
  source_files?: Record<string, string>;
  latest_stream_event?: AdrStreamEvent | null;
  latest_drift_repair?: DriftRepairEvent | null;
  pal_state?: PalState | null;
  derived?: AdrDerived | null;
};

// For compatibility with older wiring in AionProofOfLifeDashboard
export type AdrBundle = {
  stream?: AdrStreamEvent | null;
  lastRepair?: DriftRepairEvent | null;
  palState?: PalState | null;
  derived?: AdrDerived | null;
  source_files?: Record<string, string>;
  data_root?: string;
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

function toMs(ts: number): number {
  // accept seconds or ms
  return ts > 1e12 ? ts : ts > 1e9 ? ts * 1000 : ts * 1000;
}

function fmtWhen(ts?: number | null) {
  if (!ts) return "—";
  try {
    return new Date(toMs(ts)).toLocaleString();
  } catch {
    return "—";
  }
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
  adr: AdrBundle | AdrApiResponse | null;
  actionBusy: string | null;
  onInject: () => Promise<void>;
  onRun: () => Promise<void>;
}) {
  const { adr, actionBusy, onInject, onRun } = props;

  // ---- normalize shape (old bundle vs new api response) ----
  const stream: AdrStreamEvent | null = (adr as any)?.latest_stream_event ?? (adr as any)?.stream ?? null;
  const lastRepair: DriftRepairEvent | null = (adr as any)?.latest_drift_repair ?? (adr as any)?.lastRepair ?? null;
  const palState: PalState | null = (adr as any)?.pal_state ?? (adr as any)?.palState ?? null;
  const derived: AdrDerived | null = (adr as any)?.derived ?? null;

  // ---- derived ADR state ----
  const rsi = useMemo(() => {
    // backend derived.rsi is preferred
    const d = derived?.rsi;
    if (typeof d === "number") return d;

    const v = stream?.RSI ?? stream?.stability;
    return typeof v === "number" ? v : 1.0;
  }, [derived?.rsi, stream]);

  const driftEntropy = useMemo(() => {
    const v = stream?.drift_entropy ?? stream?.entropy;
    return typeof v === "number" ? v : 0.0;
  }, [stream]);

  const adrStatus = useMemo(() => {
    const s = (derived?.adr_status || "").toString();
    if (s) {
      // map backend style to UI labels
      if (s.toUpperCase() === "TRIGGERED") return "Triggered";
      if (s.toUpperCase() === "RECOVERING") return "Recovering";
      if (s.toUpperCase() === "ARMED") return "Armed";
      return s;
    }

    // fallback heuristic
    if (rsi < 0.6) return "Triggered";
    if (rsi < 0.95) return "Armed";
    return "Stable";
  }, [derived?.adr_status, rsi]);

  const adrTone =
    adrStatus === "Triggered"
      ? "text-rose-300"
      : adrStatus === "Recovering"
      ? "text-amber-200"
      : adrStatus === "Armed"
      ? "text-amber-200"
      : "text-emerald-200";

  // red pulse when:
  // - backend derived.red_pulse true, OR
  // - lastRepair timestamp changes
  const { on: redPulseOn, pulse: fireRedPulse } = usePulse(750);
  const lastRepairTsRef = useRef<number | null>(null);

  useEffect(() => {
    if (derived?.red_pulse) {
      fireRedPulse();
      return;
    }
    const ts = (lastRepair as any)?.timestamp ?? null;
    if (typeof ts === "number" && ts !== lastRepairTsRef.current) {
      lastRepairTsRef.current = ts;
      fireRedPulse();
    }
  }, [derived?.red_pulse, (lastRepair as any)?.timestamp, fireRedPulse]);

  // proof fields: support both (pre/post) and (before/after)
  const pre = (lastRepair as any)?.pre ?? (lastRepair as any)?.before ?? null;
  const post = (lastRepair as any)?.post ?? (lastRepair as any)?.after ?? null;

  const repairLabel =
    (lastRepair as any)?.event ||
    (lastRepair as any)?.type ||
    ((lastRepair as any)?.amount != null ? "inject_drift" : "") ||
    "—";

  return (
    <Card
      title="Adaptive Drift Repair (ADR) Activation"
      subtitle="GET /api/adr • sources: resonance_stream.jsonl + drift_repair.log + pal_state.json"
      right={
        <div
          className={classNames(
            "rounded-full px-3 py-1 text-xs",
            redPulseOn ? "bg-rose-500 text-white" : "bg-white/10 text-white/70"
          )}
        >
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
              <div className="mt-1 font-mono text-sm text-white">{stream?.source || stream?.source_pair || "—"}</div>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Button tone="neutral" disabled={actionBusy !== null} onClick={onInject} title="POST /api/adr/inject">
              {actionBusy === "adr_inject" ? "Injecting…" : "Inject drift"}
            </Button>
            <Button tone="primary" disabled={actionBusy !== null} onClick={onRun} title="POST /api/adr/run">
              {actionBusy === "adr_run" ? "Running…" : "Run ADR"}
            </Button>
          </div>
        </div>

        {/* Right: Repair + PAL */}
        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="mb-2 text-sm font-semibold text-white">Immune Action Panel</div>

          <div className="divide-y divide-white/10">
            <StatRow label="Latest ADR event" hint="drift_repair.log" value={repairLabel} />
            <StatRow label="Latest ADR time" hint="drift_repair.log" value={fmtWhen((lastRepair as any)?.timestamp ?? null)} />
            <StatRow
              label="ε (exploration)"
              hint="pal_state.json"
              value={<span className="font-mono">{fmt3(palState?.epsilon ?? null)}</span>}
            />
            <StatRow label="k (k-NN depth)" hint="pal_state.json" value={<span className="font-mono">{palState?.k ?? "—"}</span>} />
            <StatRow
              label="memory_weight"
              hint="pal_state.json"
              value={<span className="font-mono">{fmt3(palState?.memory_weight ?? null)}</span>}
            />
          </div>

          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3">
            <div className="text-xs font-medium uppercase tracking-wider text-white/60">Proof (before → after)</div>
            <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-xs text-white/50">ε</div>
                <div className="mt-1 font-mono text-white">
                  {fmt3(pre?.epsilon ?? null)} → {fmt3(post?.epsilon ?? null)}
                </div>
              </div>
              <div>
                <div className="text-xs text-white/50">k</div>
                <div className="mt-1 font-mono text-white">
                  {pre?.k ?? "—"} → {post?.k ?? "—"}
                </div>
              </div>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-xs text-white/50">memory_weight</div>
                <div className="mt-1 font-mono text-white">
                  {fmt3(pre?.memory_weight ?? null)} → {fmt3(post?.memory_weight ?? null)}
                </div>
              </div>
              <div>
                <div className="text-xs text-white/50">zone</div>
                <div className="mt-1 font-mono text-white">{derived?.zone ?? "—"}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}