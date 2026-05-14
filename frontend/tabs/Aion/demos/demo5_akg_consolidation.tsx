"use client";

import React, { useMemo } from "react";

/**
 * Demo05 AKG panel (Memory Consolidation)
 * - Works with BOTH the old snapshot shape and the upgraded “proof bundle” shape.
 * - Shows real evidence: last proof (before→after), top edges, and feed status.
 */

export const demo05Meta = {
  id: "demo05-akg",
  pillar: "Pillar 5",
  title: "Memory Consolidation (AKG Triplet Strengthening)",
  testName: "AKG Edge Reinforcement",
  copy:
    "Repeated correct recall thickens AKG edges. Strength rises toward 1.0, optionally decays by half-life. This is the graph-native proof that learning happened.",
} as const;

/* ---------------- Types (tolerant) ---------------- */

// Old edge shape
type AkgEdgeOld = { s: string; r: string; o: string; strength: number; count?: number };

// New edge shape (proof bundle)
type AkgEdgeNew = {
  src?: string;
  dst?: string;
  s?: string;
  r?: string;
  o?: string;
  w?: number; // weight/strength
  strength?: number;
  count?: number;
  updated_ts?: number;
};

type AkgProof = {
  timestamp?: number;
  ts?: number;
  type?: string;
  edge?: any;
  before?: { w?: number; strength?: number; count?: number };
  after?: { w?: number; strength?: number; count?: number };
  pre?: { w?: number; strength?: number; count?: number };
  post?: { w?: number; strength?: number; count?: number };
};

export type AkgSnapshot = any;

/* ---------------- Helpers ---------------- */

function clamp01(x: any) {
  const n = typeof x === "number" ? x : x != null ? Number(x) : NaN;
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

function pct(x: any) {
  return `${Math.round(clamp01(x) * 100)}%`;
}

function fmt3(x: any) {
  const n = typeof x === "number" ? x : x != null ? Number(x) : NaN;
  return Number.isFinite(n) ? n.toFixed(3) : "—";
}

function fmt0(x: any) {
  const n = typeof x === "number" ? x : x != null ? Number(x) : NaN;
  return Number.isFinite(n) ? String(Math.round(n)) : "—";
}

function fmtAgeMs(ageMs?: number | null) {
  if (ageMs == null) return "—";
  const ms = Math.max(0, ageMs);
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  return `${(s / 60).toFixed(1)}m`;
}

function pickNum(obj: any, keys: string[]): number | null {
  if (!obj) return null;
  for (const k of keys) {
    const v = obj?.[k] ?? obj?.[k.replace(/[\s\-]/g, "_")] ?? obj?.[k.replace(/_/g, "")];
    const n = typeof v === "number" ? v : v != null ? Number(v) : NaN;
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function pickStr(obj: any, keys: string[]): string | null {
  if (!obj) return null;
  for (const k of keys) {
    const v = obj?.[k] ?? obj?.[k.replace(/[\s\-]/g, "_")] ?? obj?.[k.replace(/_/g, "")];
    if (v != null && String(v).trim() !== "") return String(v);
  }
  return null;
}

function getEdgeLabel(e: any) {
  const s = pickStr(e, ["s", "src", "subject"]) ?? "—";
  const r = pickStr(e, ["r", "rel", "relation"]) ?? "—";
  const o = pickStr(e, ["o", "dst", "object"]) ?? "—";
  return { s, r, o };
}

function getEdgeStrength(e: any) {
  return (
    pickNum(e, ["strength", "w", "weight"]) ??
    (e?.after ? pickNum(e.after, ["strength", "w", "weight"]) : null) ??
    0
  );
}

function getEdgeCount(e: any) {
  return pickNum(e, ["count", "n", "hits"]) ?? null;
}

function coerceTopEdges(akg: any): any[] {
  const arr =
    akg?.top_edges ??
    akg?.topEdges ??
    akg?.edges ??
    akg?.state?.top_edges ??
    akg?.derived?.top_edges ??
    [];
  return Array.isArray(arr) ? arr : [];
}

function coerceProof(akg: any): AkgProof | null {
  const p =
    akg?.proof ??
    akg?.last_proof ??
    akg?.lastProof ??
    akg?.derived?.proof ??
    akg?.latest_proof ??
    null;
  if (p && typeof p === "object") return p as AkgProof;
  return null;
}

function computeAgeMs(akg: any): number | null {
  // prefer explicit age_ms
  const age =
    pickNum(akg, ["age_ms", "ageMs"]) ??
    pickNum(akg?.derived, ["age_ms", "ageMs"]) ??
    null;
  if (age != null) return age;

  // else compute from ts fields
  const ts =
    pickNum(akg, ["ts", "timestamp"]) ??
    pickNum(akg?.derived, ["ts", "timestamp"]) ??
    pickNum(akg?.state, ["ts", "timestamp"]) ??
    null;

  if (ts == null) return null;
  // if seconds epoch
  const ms = ts > 1e12 ? ts : ts > 1e9 ? ts * 1000 : null;
  if (ms == null) return null;
  return Math.max(0, Date.now() - ms);
}

/* ---------------- UI atoms ---------------- */

function Chip(props: { tone: "good" | "warn" | "bad" | "neutral"; children: React.ReactNode }) {
  const cls =
    props.tone === "good"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : props.tone === "warn"
      ? "border-amber-200 bg-amber-50 text-amber-700"
      : props.tone === "bad"
      ? "border-rose-200 bg-rose-50 text-rose-700"
      : "border-slate-200 bg-white text-slate-700";

  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[10px] font-bold uppercase tracking-[0.22em] ${cls}`}>
      {props.children}
    </span>
  );
}

function toneFromStrength(w: number) {
  if (w >= 0.95) return "good";
  if (w >= 0.6) return "warn";
  return "bad";
}

function ButtonPill(props: {
  onClick: () => void;
  disabled?: boolean;
  busy?: boolean;
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <button
      onClick={props.onClick}
      disabled={props.disabled}
      title={props.title}
      className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/80 hover:bg-white/10 disabled:opacity-50"
    >
      {props.children}
    </button>
  );
}

/* ---------------- Component ---------------- */

export function Demo05AkgPanel(props: {
  akg: AkgSnapshot | null;
  actionBusy: string | null;
  onReset: () => void;
  onStep: () => void;
  onRun: () => void;
}) {
  const akg = props.akg;

  const model = useMemo(() => {
    const edgesTotal =
      pickNum(akg, ["edges_total", "edgesTotal", "edges_count", "edgesCount", "edge_count"]) ??
      pickNum(akg?.derived, ["edges_total", "edges_count", "edgesCount"]) ??
      pickNum(akg?.state, ["edges_total", "edges_count", "edgesCount"]) ??
      null;

    const alpha =
      pickNum(akg, ["alpha", "α"]) ??
      pickNum(akg?.state, ["alpha", "α"]) ??
      pickNum(akg?.derived, ["alpha", "α"]) ??
      null;

    const halfLife =
      pickNum(akg, ["half_life_s", "halfLifeS", "half_life"]) ??
      pickNum(akg?.state, ["half_life_s", "halfLifeS"]) ??
      pickNum(akg?.derived, ["half_life_s", "halfLifeS"]) ??
      null;

    const decayEnabled =
      (() => {
        const v =
          akg?.decay_enabled ??
          akg?.decayEnabled ??
          akg?.state?.decay_enabled ??
          akg?.state?.decayEnabled ??
          akg?.derived?.decay_enabled ??
          akg?.derived?.decayEnabled;
        if (typeof v === "boolean") return v;
        if (v == null) return null;
        const s = String(v).toLowerCase();
        if (s === "true") return true;
        if (s === "false") return false;
        return null;
      })() ?? null;

    const topEdges = coerceTopEdges(akg);
    const proof = coerceProof(akg);
    const ageMs = computeAgeMs(akg);

    return { edgesTotal, alpha, halfLife, decayEnabled, topEdges, proof, ageMs };
  }, [akg]);

  const feedChip = useMemo(() => {
    if (!akg) {
      return (
        <Chip tone="warn">
          <span className="h-2 w-2 rounded-full bg-amber-500" />
          <span>NO_FEED</span>
        </Chip>
      );
    }
    if (model.ageMs == null) {
      return (
        <Chip tone="warn">
          <span className="h-2 w-2 rounded-full bg-amber-500" />
          <span>UNKNOWN_AGE</span>
        </Chip>
      );
    }
    if (model.ageMs <= 2000) {
      return (
        <Chip tone="good">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          <span>PULSE {fmtAgeMs(model.ageMs)}</span>
        </Chip>
      );
    }
    if (model.ageMs <= 10000) {
      return (
        <Chip tone="warn">
          <span className="h-2 w-2 rounded-full bg-amber-500" />
          <span>AGING {fmtAgeMs(model.ageMs)}</span>
        </Chip>
      );
    }
    return (
      <Chip tone="bad">
        <span className="h-2 w-2 rounded-full bg-rose-500" />
        <span>STALE {fmtAgeMs(model.ageMs)}</span>
      </Chip>
    );
  }, [akg, model.ageMs]);

  const lastProofView = useMemo(() => {
    const p = model.proof;
    if (!p) return null;

    const ts = pickNum(p, ["timestamp", "ts"]);
    const ms = ts ? (ts > 1e12 ? ts : ts > 1e9 ? ts * 1000 : null) : null;

    const beforeW =
      pickNum(p, ["before_w"]) ??
      pickNum(p?.before, ["w", "weight", "strength"]) ??
      pickNum(p?.pre, ["w", "weight", "strength"]) ??
      null;

    const afterW =
      pickNum(p, ["after_w"]) ??
      pickNum(p?.after, ["w", "weight", "strength"]) ??
      pickNum(p?.post, ["w", "weight", "strength"]) ??
      null;

    const edge = p.edge ?? null;
    const { s, r, o } = edge ? getEdgeLabel(edge) : { s: "—", r: "—", o: "—" };

    return {
      when: ms ? new Date(ms).toLocaleString() : "—",
      s,
      r,
      o,
      beforeW,
      afterW,
    };
  }, [model.proof]);

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3 text-sm text-white/70">
          <div className="flex items-center gap-2">
            {feedChip}
            <span className="text-white/40">•</span>
          </div>

          <div>
            edges: <span className="font-semibold text-white">{model.edgesTotal ?? "—"}</span>
            <span className="text-white/40"> • </span>
            α: <span className="font-mono text-white/90">{model.alpha != null ? fmt3(model.alpha) : "—"}</span>
            <span className="text-white/40"> • </span>
            half-life: <span className="font-mono text-white/90">{model.halfLife != null ? fmt0(model.halfLife) : "—"}</span>s
            <span className="text-white/40"> • </span>
            decay:{" "}
            <span className="font-mono text-white/90">
              {model.decayEnabled == null ? "—" : model.decayEnabled ? "ON" : "OFF"}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <ButtonPill
            onClick={props.onReset}
            disabled={!!props.actionBusy}
            title="POST /api/demo/akg/reset"
          >
            {props.actionBusy === "akg_reset" ? "Resetting…" : "Reset"}
          </ButtonPill>

          <ButtonPill
            onClick={props.onStep}
            disabled={!!props.actionBusy}
            title="POST /api/demo/akg/step"
          >
            {props.actionBusy === "akg_step" ? "Stepping…" : "Step"}
          </ButtonPill>

          <ButtonPill
            onClick={props.onRun}
            disabled={!!props.actionBusy}
            title="POST /api/demo/akg/run?rounds=400"
          >
            {props.actionBusy === "akg_run" ? "Running…" : "Run 400"}
          </ButtonPill>
        </div>
      </div>

      {/* Proof strip (shows real before→after if backend provides it) */}
      <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-4">
        <div className="mb-2 flex items-center justify-between gap-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-white/70">Proof (before → after)</div>
          <div className="text-xs text-white/50">{lastProofView?.when ?? "—"}</div>
        </div>

        {lastProofView ? (
          <>
            <div className="text-xs text-white/85">
              <span className="font-semibold">{lastProofView.s}</span>{" "}
              <span className="text-white/50">{lastProofView.r}</span>{" "}
              <span className="font-semibold">{lastProofView.o}</span>
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-3">
              <Chip tone={toneFromStrength(clamp01(lastProofView.afterW ?? lastProofView.beforeW ?? 0)) as any}>
                <span>W</span>
                <span className="font-mono">
                  {fmt3(lastProofView.beforeW)} → {fmt3(lastProofView.afterW)}
                </span>
              </Chip>
            </div>
          </>
        ) : (
          <div className="text-xs text-white/50">
            No proof emitted yet (backend must append an edge update with before→after).
          </div>
        )}
      </div>

      {/* Top edges */}
      <div className="mt-4 space-y-2">
        {(model.topEdges || []).slice(0, 12).map((raw, idx) => {
          const { s, r, o } = getEdgeLabel(raw);
          const w = getEdgeStrength(raw);
          const c = getEdgeCount(raw);
          return (
            <div key={`${s}|${r}|${o}|${idx}`} className="rounded-xl border border-white/10 bg-black/20 p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="text-xs text-white/85">
                  <span className="font-semibold">{s}</span>{" "}
                  <span className="text-white/50">{r}</span>{" "}
                  <span className="font-semibold">{o}</span>
                </div>
                <div className="text-xs text-white/60">
                  strength <span className="font-mono text-white/90">{fmt3(w)}</span>
                  {c != null ? (
                    <>
                      <span className="text-white/40"> • </span>
                      count <span className="font-mono text-white/90">{fmt0(c)}</span>
                    </>
                  ) : null}
                </div>
              </div>

              <div className="mt-2 h-2 w-full rounded-full bg-white/10">
                <div className="h-2 rounded-full bg-white/60" style={{ width: pct(w) }} />
              </div>
            </div>
          );
        })}

        {!akg ? <div className="text-xs text-white/50">Waiting for /api/akg…</div> : null}
        {akg && (!model.topEdges || model.topEdges.length === 0) ? (
          <div className="text-xs text-white/50">Feed is online but no edges are being emitted yet.</div>
        ) : null}
      </div>
    </div>
  );
}