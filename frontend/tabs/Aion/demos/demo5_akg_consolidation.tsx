"use client";

import React from "react";

export const demo05Meta = {
  id: "demo05-akg",
  pillar: "Pillar 5",
  title: "Memory Consolidation (AKG Triplet Strengthening)",
  testName: "AKG Edge Reinforcement",
  copy:
    "Repeated correct recall thickens AKG edges. Strength rises toward 1.0, optionally decays by half-life. This is the graph-native proof that learning happened.",
};

type AkgEdge = { s: string; r: string; o: string; strength: number; count: number };
export type AkgSnapshot = {
  ts: number;
  edges_total: number;
  alpha: number;
  half_life_s: number;
  top_edges: AkgEdge[];
};

function pct(x: number) {
  const v = Math.max(0, Math.min(1, x || 0));
  return `${Math.round(v * 100)}%`;
}

export function Demo05AkgPanel(props: {
  akg: AkgSnapshot | null;
  actionBusy: string | null;
  onReset: () => void;
  onStep: () => void;
  onRun: () => void;
}) {
  const akg = props.akg;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm text-white/70">
          edges: <span className="font-semibold text-white">{akg?.edges_total ?? "—"}</span>{" "}
          <span className="text-white/40">•</span>{" "}
          α: <span className="font-mono text-white/90">{akg?.alpha ?? "—"}</span>{" "}
          <span className="text-white/40">•</span>{" "}
          half-life: <span className="font-mono text-white/90">{akg?.half_life_s ?? "—"}</span>s
        </div>

        <div className="flex gap-2">
          <button
            onClick={props.onReset}
            disabled={!!props.actionBusy}
            className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/80 hover:bg-white/10 disabled:opacity-50"
          >
            {props.actionBusy === "akg_reset" ? "Resetting…" : "Reset"}
          </button>
          <button
            onClick={props.onStep}
            disabled={!!props.actionBusy}
            className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/80 hover:bg-white/10 disabled:opacity-50"
          >
            {props.actionBusy === "akg_step" ? "Stepping…" : "Step"}
          </button>
          <button
            onClick={props.onRun}
            disabled={!!props.actionBusy}
            className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/80 hover:bg-white/10 disabled:opacity-50"
          >
            {props.actionBusy === "akg_run" ? "Running…" : "Run 400"}
          </button>
        </div>
      </div>

      <div className="mt-4 space-y-2">
        {(akg?.top_edges || []).slice(0, 12).map((e, idx) => (
          <div key={`${e.s}|${e.r}|${e.o}|${idx}`} className="rounded-xl border border-white/10 bg-black/20 p-3">
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs text-white/85">
                <span className="font-semibold">{e.s}</span>{" "}
                <span className="text-white/50">{e.r}</span>{" "}
                <span className="font-semibold">{e.o}</span>
              </div>
              <div className="text-xs text-white/60">
                strength <span className="font-mono text-white/90">{e.strength.toFixed(3)}</span>{" "}
                <span className="text-white/40">•</span>{" "}
                count <span className="font-mono text-white/90">{e.count}</span>
              </div>
            </div>

            <div className="mt-2 h-2 w-full rounded-full bg-white/10">
              <div
                className="h-2 rounded-full bg-white/60"
                style={{ width: pct(e.strength) }}
              />
            </div>
          </div>
        ))}

        {!akg ? <div className="text-xs text-white/50">Waiting for /api/akg…</div> : null}
      </div>
    </div>
  );
}