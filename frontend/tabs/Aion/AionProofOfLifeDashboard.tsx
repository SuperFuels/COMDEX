// frontend/tabs/Aion/AionProofOfLifeDashboard.tsx
"use client";

import React, { useEffect, useMemo, useState } from "react";

import type { PhiBundle, AdrBundle, HeartbeatEnvelope, ReflexEnvelope, AkgSnapshot } from "./demos/types";

import { demo01Meta, Demo01MetabolismPanel } from "./demos/demo01_metabolism";
import { demo02Meta, Demo02AdrPanel } from "./demos/demo02_immune_adr";
import { demo03Meta, Demo03HeartbeatPanel } from "./demos/Demo03Heartbeat";
import { demo04Meta, Demo04ReflexGridPanel } from "./demos/demo04_reflex_grid";
import { demo05Meta, Demo05AkgPanel } from "./demos/demo5_akg_consolidation";

import { demo00Meta } from "./demos/demo00_homeostasis_real";
import { demo06Meta, Demo06MirrorPanel } from "./demos/demo06_mirror_reflection";

import AionCognitiveDashboard from "./AionCognitiveDashboard";

/* ---------------- Types (tolerant; don’t block compilation) ---------------- */
type HomeostasisEnvelope = any; // GET /api/aion/dashboard
type MirrorEnvelope = any; // GET /aion-demo/api/mirror

/* ---------------- URL helpers ---------------- */

function stripSlash(s: string) {
  return (s || "").trim().replace(/\/+$/, "");
}

/**
 * IMPORTANT:
 * - This dashboard should be driven by the BACKEND ORIGIN only.
 * - DO NOT use NEXT_PUBLIC_AION_DEMO_HTTP_BASE here.
 */
function resolveBackendHttpBase(): string {
  const env =
    (process.env.NEXT_PUBLIC_API_ORIGIN as string | undefined) ||
    (process.env.NEXT_PUBLIC_GLYPHNET_HTTP_BASE as string | undefined) ||
    (process.env.NEXT_PUBLIC_API_URL as string | undefined) ||
    (process.env.NEXT_PUBLIC_API_BASE as string | undefined) ||
    (process.env.NEXT_PUBLIC_AION_API_BASE as string | undefined) ||
    "";

  const cleaned = stripSlash(env).replace(/\/api$/i, "").replace(/\/aion-demo$/i, "");
  if (cleaned) return cleaned;

  // Local dev convenience (Next at :3000, backend at :8080)
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    const port = window.location.port;
    const isLocal = host === "localhost" || host === "127.0.0.1";
    if (isLocal && port === "3000") return "http://127.0.0.1:8080";

    // If you are on Vercel/Prod, same-origin is fine because Next rewrites /api/*
    // NOTE: returning "" makes fetch("/api/...") hit same-origin.
    return "";
  }

  return "";
}

function joinUrl(base: string, path: string) {
  const p = path.startsWith("/") ? path : `/${path}`;
  return base ? stripSlash(base) + p : p;
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  const ct = res.headers.get("content-type") || "";
  const text = await res.text().catch(() => "");

  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}${text ? `: ${text.slice(0, 160)}` : ""}`);
  }
  if (!ct.includes("application/json")) {
    throw new Error(`Expected JSON but got "${ct || "unknown"}"`);
  }
  return JSON.parse(text) as T;
}

async function postJson(url: string, body?: any): Promise<void> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body != null ? JSON.stringify(body) : undefined,
  });

  const text = await res.text().catch(() => "");
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}${text ? `: ${text.slice(0, 160)}` : ""}`);
}

/* ---------------- Small UI helpers ---------------- */

function classNames(...xs: Array<string | false | null | undefined>) {
  return xs.filter(Boolean).join(" ");
}

function safeNum(x: any): number | null {
  const n = typeof x === "number" ? x : x != null ? Number(x) : NaN;
  return Number.isFinite(n) ? n : null;
}

function fmtAgeMs(ageMs?: number | null) {
  if (ageMs == null) return "—";
  const ms = Math.max(0, ageMs);
  if (ms < 1_000) return `${ms.toFixed(0)}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  return `${(s / 60).toFixed(1)}m`;
}

function ageFromLastUpdate(x: any): number | null {
  const lu = x?.last_update ?? x?.state?.last_update ?? x?.snapshot?.last_update;
  if (!lu) return null;
  const t = Date.parse(String(lu));
  if (!Number.isFinite(t)) return null;
  return Math.max(0, Date.now() - t);
}

const BRAND = { blue: "#1B74E4" };

/* ---------------- Chips ---------------- */

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
    <span
      className={classNames(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[10px] font-bold uppercase tracking-[0.22em]",
        cls
      )}
    >
      {props.children}
    </span>
  );
}

function ageChip(ageMs: number | null, okMs = 2000, warnMs = 6000) {
  if (ageMs == null) {
    return (
      <Chip tone="warn">
        <span className="h-2 w-2 rounded-full bg-amber-500" />
        <span>NO_FEED</span>
      </Chip>
    );
  }
  if (ageMs <= okMs) {
    return (
      <Chip tone="good">
        <span className="h-2 w-2 rounded-full bg-emerald-500" />
        <span>PULSE {Math.round(ageMs)}ms</span>
      </Chip>
    );
  }
  if (ageMs <= warnMs) {
    return (
      <Chip tone="warn">
        <span className="h-2 w-2 rounded-full bg-amber-500" />
        <span>AGING {Math.round(ageMs)}ms</span>
      </Chip>
    );
  }
  return (
    <Chip tone="bad">
      <span className="h-2 w-2 rounded-full bg-rose-500" />
      <span>STALE {Math.round(ageMs)}ms</span>
    </Chip>
  );
}

/* ---------------- Brand-aligned section card ---------------- */

function PillarSection(props: {
  id: string;
  container: React.ReactNode;
  title: string;
  pillar: string;
  testName: string;
  copy: string;
  tone?: "light" | "dark";
}) {
  const tone = props.tone || "light";

  const stage =
    tone === "dark"
      ? "rounded-3xl border border-slate-900/10 bg-slate-950/[0.90] p-6 shadow-sm"
      : "rounded-3xl border border-slate-200 bg-white p-0 shadow-sm";

  return (
    <section
      id={props.id}
      className="grid grid-cols-1 gap-8 py-10 lg:grid-cols-5 border-b border-slate-200 last:border-0"
    >
      <div className="lg:col-span-3">
        <div className={stage}>{props.container}</div>
      </div>

      <div className="lg:col-span-2 flex items-center">
        <div className="w-full rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em]" style={{ color: BRAND.blue }}>
            {props.pillar}
          </div>
          <div className="mt-3 text-xl font-black tracking-tight text-slate-900 uppercase italic">{props.title}</div>
          <div className="mt-2 font-mono text-[11px] uppercase tracking-widest text-slate-500">
            ENGINE_MODE: <span className="text-slate-800">{props.testName}</span>
          </div>
          <div className="mt-6 h-px w-10" style={{ backgroundColor: `${BRAND.blue}99` }} />
          <p className="mt-6 text-sm leading-relaxed text-slate-600 font-medium">{props.copy}</p>
        </div>
      </div>
    </section>
  );
}

/* ---------------- ADR adapter ----------------
Backend (current): GET /api/adr returns:
  { latest_stream_event, latest_drift_repair, pal_state, derived, ... }
UI expects AdrBundle:
  { stream, lastRepair, palState }
---------------------------------------------- */

function adaptAdr(raw: any): AdrBundle {
  if (!raw || typeof raw !== "object") return { stream: null, lastRepair: null, palState: null } as any;

  const stream = raw.stream ?? raw.latest_stream_event ?? raw.latestStreamEvent ?? null;
  const lastRepair = raw.lastRepair ?? raw.latest_drift_repair ?? raw.latestDriftRepair ?? null;
  const palState = raw.palState ?? raw.pal_state ?? raw.palStateJson ?? null;

  // pass-through useful fields (panel ignores them but great for debug)
  const extra = {
    derived: raw.derived,
    source_files: raw.source_files,
    data_root: raw.data_root,
  };

  return { stream, lastRepair, palState, ...(extra as any) } as any;
}

/* ---------------- Akg adapter (tolerant) ---------------- */

function adaptAkg(raw: any): AkgSnapshot | null {
  if (!raw) return null;
  if (raw.top_edges || raw.edges_total != null) return raw as AkgSnapshot;

  const candidate = raw.state ?? raw.snapshot ?? raw.data ?? null;
  if (candidate && (candidate.top_edges || candidate.edges_total != null)) return candidate as AkgSnapshot;

  return raw as AkgSnapshot; // last resort
}

/* ---------------- Poller (with per-feed errors) ---------------- */

type FeedErrs = Partial<Record<"homeo" | "phi" | "adr" | "hb" | "reflex" | "akg" | "mirror", string>>;

function useAionDemoData(pollMs = 1500) {
  const base = useMemo(() => resolveBackendHttpBase(), []);
  const apiBase = base; // backend root
  const demoBase = useMemo(() => (base ? joinUrl(base, "/aion-demo") : "/aion-demo"), [base]);

  const [homeostasis, setHomeostasis] = useState<HomeostasisEnvelope | null>(null);
  const [phi, setPhi] = useState<PhiBundle | null>(null);
  const [adr, setAdr] = useState<AdrBundle | null>(null);
  const [heartbeat, setHeartbeat] = useState<HeartbeatEnvelope | null>(null);
  const [reflex, setReflex] = useState<ReflexEnvelope | null>(null);
  const [akg, setAkg] = useState<AkgSnapshot | null>(null);
  const [mirror, setMirror] = useState<MirrorEnvelope | null>(null);

  const [loading, setLoading] = useState(true);
  const [errs, setErrs] = useState<FeedErrs>({});

  useEffect(() => {
    let cancelled = false;
    let t: any = null;

    const tick = async () => {
      const urls = {
        // main (non-demo)
        homeo: joinUrl(apiBase, "/api/aion/dashboard"),
        adr: joinUrl(apiBase, "/api/adr"), // ✅ ADR lives on main router

        // demo routes
        phi: joinUrl(demoBase, "/api/phi"),
        hb: joinUrl(demoBase, "/api/heartbeat?namespace=demo"),
        reflex: joinUrl(demoBase, "/api/reflex"),
        akg: joinUrl(demoBase, "/api/akg"),
        mirror: joinUrl(demoBase, "/api/mirror"),
      };

      const nextErrs: FeedErrs = {};

      try {
        const results = await Promise.allSettled([
          fetchJson<HomeostasisEnvelope>(urls.homeo),
          fetchJson<PhiBundle>(urls.phi),
          fetchJson<any>(urls.adr), // raw -> adaptAdr()
          fetchJson<HeartbeatEnvelope>(urls.hb),
          fetchJson<ReflexEnvelope>(urls.reflex),
          fetchJson<any>(urls.akg), // raw -> adaptAkg()
          fetchJson<MirrorEnvelope>(urls.mirror),
        ]);

        if (cancelled) return;

        const [homeoRes, phiRes, adrRes, hbRes, reflexRes, akgRes, mirrorRes] = results;

        if (homeoRes.status === "fulfilled") setHomeostasis(homeoRes.value);
        else nextErrs.homeo = String((homeoRes as any).reason?.message || (homeoRes as any).reason || "error");

        if (phiRes.status === "fulfilled") setPhi(phiRes.value);
        else nextErrs.phi = String((phiRes as any).reason?.message || (phiRes as any).reason || "error");

        if (adrRes.status === "fulfilled") setAdr(adaptAdr(adrRes.value));
        else nextErrs.adr = String((adrRes as any).reason?.message || (adrRes as any).reason || "error");

        if (hbRes.status === "fulfilled") setHeartbeat(hbRes.value);
        else nextErrs.hb = String((hbRes as any).reason?.message || (hbRes as any).reason || "error");

        if (reflexRes.status === "fulfilled") setReflex(reflexRes.value);
        else nextErrs.reflex = String((reflexRes as any).reason?.message || (reflexRes as any).reason || "error");

        if (akgRes.status === "fulfilled") setAkg(adaptAkg(akgRes.value));
        else nextErrs.akg = String((akgRes as any).reason?.message || (akgRes as any).reason || "error");

        if (mirrorRes.status === "fulfilled") setMirror(mirrorRes.value);
        else nextErrs.mirror = String((mirrorRes as any).reason?.message || (mirrorRes as any).reason || "error");

        setErrs(nextErrs);
      } finally {
        if (!cancelled) setLoading(false);
        t = setTimeout(tick, pollMs);
      }
    };

    tick();
    return () => {
      cancelled = true;
      if (t) clearTimeout(t);
    };
  }, [pollMs, apiBase, demoBase]);

  const anyOk = !!(homeostasis || phi || adr || heartbeat || reflex || akg || mirror);
  const errSummary = useMemo(() => {
    if (loading) return null;
    if (Object.keys(errs).length === 0) return null;
    if (!anyOk) return "All feeds offline";
    return null;
  }, [errs, anyOk, loading]);

  return {
    base,
    apiBase,
    demoBase,
    homeostasis,
    phi,
    adr,
    heartbeat,
    reflex,
    akg,
    mirror,
    errs,
    loading,
    errSummary,
  };
}

/* ---------------- Phase Closure Monitor (keep tolerant) ---------------- */

function pickMetricLoose(src: any, keys: string[]): number | null {
  if (!src) return null;
  for (const k of keys) {
    const v = src?.[k];
    const n = safeNum(v);
    if (n != null) return n;

    const k2 = k.replace(/[\s\-]/g, "_");
    const n2 = safeNum(src?.[k2]);
    if (n2 != null) return n2;

    const k3 = k.replace(/_/g, "");
    const n3 = safeNum(src?.[k3]);
    if (n3 != null) return n3;
  }
  return null;
}

function pickFirstNumber(sources: any[], keys: string[]): number | null {
  for (const s of sources) {
    const v = pickMetricLoose(s, keys);
    if (v != null) return v;
  }
  return null;
}

function pickFirstString(sources: any[], keys: string[]): string | null {
  for (const s of sources) {
    if (!s) continue;
    for (const k of keys) {
      const v = s?.[k] ?? s?.[k.replace(/[\s\-]/g, "_")] ?? s?.[k.replace(/_/g, "")];
      if (v != null && String(v).trim() !== "") return String(v);
    }
  }
  return null;
}

function pickFirstBool(sources: any[], keys: string[]): boolean | null {
  for (const s of sources) {
    if (!s) continue;
    for (const k of keys) {
      const v = s?.[k] ?? s?.[k.replace(/[\s\-]/g, "_")] ?? s?.[k.replace(/_/g, "")];
      if (typeof v === "boolean") return v;
      if (v == null) continue;
      const sv = String(v).toLowerCase();
      if (sv === "true") return true;
      if (sv === "false") return false;
    }
  }
  return null;
}

function extractPhaseClosure(homeostasis: any | null, mirror: any | null) {
  const homeoLast =
    homeostasis?.homeostasis?.last ??
    homeostasis?.homeostasis ??
    homeostasis?.last ??
    homeostasis?.state?.last ??
    homeostasis?.state ??
    homeostasis ??
    null;

  const homeoMetrics =
    homeoLast?.metrics ??
    homeoLast?.state?.metrics ??
    homeoLast?.snapshot?.metrics ??
    homeoLast ??
    null;

  const mirrorState = mirror?.state ?? mirror?.snapshot ?? mirror?.mirror ?? mirror ?? null;

  const homeoSources = [homeoMetrics, homeoLast, homeostasis].filter(Boolean);
  const mirrorSources = [mirrorState].filter(Boolean);

  const H = (s: any) => [s, s?.metrics, s?.state, s?.state?.metrics, s?.snapshot, s?.snapshot?.metrics].filter(Boolean);

  const homeoDeep = homeoSources.flatMap(H);
  const mirrorDeep = mirrorSources.flatMap(H);

  const closure = pickFirstNumber(homeoDeep, ["⟲", "closure", "phase_closure", "phaseClosure", "equilibrium", "eq", "stability", "S"]);

  const dPhi = pickFirstNumber(homeoDeep, [
    "ΔΦ",
    "dPhi",
    "delta_phi",
    "deltaPhi",
    "phi_drift",
    "drift_phi",
    "drift",
    "resonance_delta",
  ]);

  const sqi =
    pickFirstNumber(homeoDeep, [
      "sqi_checkpoint",
      "sqiCheckpoint",
      "SQI",
      "sqi",
      "checkpoint_sqi",
      "Φ_coherence",
      "phi_coherence",
      "coherence",
      "C",
    ]) ??
    pickFirstNumber(mirrorDeep, [
      "sqi_checkpoint",
      "sqiCheckpoint",
      "SQI",
      "sqi",
      "checkpoint_sqi",
      "Φ_coherence",
      "phi_coherence",
      "coherence",
      "C",
    ]);

  const rho =
    pickFirstNumber(homeoDeep, ["ρ", "rho", "Phi_coherence", "Φ_coherence", "phi_coherence"]) ??
    pickFirstNumber(mirrorDeep, ["ρ", "rho", "Phi_coherence", "Φ_coherence", "phi_coherence"]);

  const Ibar =
    pickFirstNumber(homeoDeep, ["Ī", "Ibar", "Ī", "iota", "Φ_entropy", "Phi_entropy", "phi_entropy"]) ??
    pickFirstNumber(mirrorDeep, ["Ī", "Ibar", "Ī", "iota", "Φ_entropy", "Phi_entropy", "phi_entropy"]);

  const locked =
    pickFirstBool(homeoDeep, ["locked", "lock", "is_locked", "isLocked"]) ??
    pickFirstBool(mirrorDeep, ["locked", "lock", "is_locked", "isLocked"]);

  const lockId =
    pickFirstString(homeoDeep, ["lock_id", "lockId", "lockID", "LOCK_ID", "id", "lock"]) ??
    pickFirstString(mirrorDeep, ["lock_id", "lockId", "lockID", "LOCK_ID", "id", "lock"]);

  const ageMs =
    safeNum(homeostasis?.age_ms) ??
    safeNum(homeoLast?.age_ms) ??
    safeNum(homeoMetrics?.age_ms) ??
    ageFromLastUpdate(homeostasis) ??
    ageFromLastUpdate(homeoLast) ??
    (() => {
      const ts =
        homeostasis?.timestamp ??
        homeostasis?.ts ??
        homeoLast?.timestamp ??
        homeoLast?.ts ??
        homeoMetrics?.timestamp ??
        homeoMetrics?.ts ??
        null;

      const t =
        typeof ts === "number"
          ? ts > 1e12
            ? ts
            : ts > 1e9
            ? ts * 1000
            : null
          : ts
          ? Date.parse(String(ts))
          : null;

      return Number.isFinite(t as number) ? Math.max(0, Date.now() - (t as number)) : null;
    })() ??
    safeNum(mirror?.age_ms) ??
    ageFromLastUpdate(mirror) ??
    null;

  return { closure, dPhi, sqi, rho, Ibar, locked, lockId, ageMs };
}

function MetricLine(props: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/10 py-2 last:border-0">
      <div className="font-mono text-[11px] uppercase tracking-widest text-slate-300">{props.label}</div>
      <div className="font-mono text-[12px] font-bold tracking-wider text-white">{props.value}</div>
    </div>
  );
}

function PhaseClosureMonitorPanel(props: { homeostasis: any | null; mirror: any | null }) {
  const THRESH = 0.975;

  const { closure, dPhi, sqi, rho, Ibar, locked, lockId, ageMs } = useMemo(
    () => extractPhaseClosure(props.homeostasis, props.mirror),
    [props.homeostasis, props.mirror]
  );

  const noFeed = ageMs == null || ageMs > 120_000;

  const isLocked = locked === true || (closure != null && closure >= THRESH);
  const status = noFeed ? "NO_FEED" : isLocked ? "FIELD_LOCKED" : "ALIGNING";

  const badge = noFeed ? (
    <Chip tone="bad">
      <span className="h-2 w-2 rounded-full bg-rose-500" />
      <span>NO_FEED</span>
    </Chip>
  ) : isLocked ? (
    <Chip tone="good">
      <span className="h-2 w-2 rounded-full bg-emerald-500" />
      <span>LOCKED</span>
    </Chip>
  ) : (
    <Chip tone="warn">
      <span className="h-2 w-2 rounded-full bg-amber-500" />
      <span>ALIGNING</span>
    </Chip>
  );

  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/[0.90] p-8 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-blue-300">Integrity</div>
          <div className="mt-2 text-2xl font-black tracking-tight text-white uppercase italic">Phase Closure Monitor</div>
          <div className="mt-3 font-mono text-[11px] uppercase tracking-widest text-slate-300">
            ⟲ ≥ <span className="text-white">{THRESH.toFixed(3)}</span>
          </div>
          <div className="mt-3 text-sm font-medium text-slate-300">
            {noFeed
              ? "Homeostasis producer is not emitting (or dashboard route is returning a stub)."
              : "Proof-of-life: stability is detected internally, then promoted to a lockable state."}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {badge}
          <div className="font-mono text-[11px] uppercase tracking-widest text-slate-400">
            AGE: <span className="text-slate-200">{fmtAgeMs(ageMs)}</span>
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-5">
        <div className="mb-3 font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-300">{status}</div>
        <MetricLine label="⟲" value={closure != null ? closure.toFixed(4) : "—"} />
        <MetricLine label="ΔΦ" value={dPhi != null ? dPhi.toFixed(6) : "—"} />
        <MetricLine label="SQI" value={sqi != null ? sqi.toFixed(6) : "—"} />
        <MetricLine label="ρ" value={rho != null ? rho.toFixed(6) : "—"} />
        <MetricLine label="Ī" value={Ibar != null ? Ibar.toFixed(6) : "—"} />
        <MetricLine label="lock_id" value={lockId ?? "—"} />
      </div>
    </div>
  );
}

/* ---------------- Page ---------------- */

export default function AionProofOfLifeDashboard() {
  const { base, apiBase, demoBase, homeostasis, phi, adr, heartbeat, reflex, akg, mirror, errs, loading, errSummary } =
    useAionDemoData(1500);

  const [actionBusy, setActionBusy] = useState<string | null>(null);

  async function runBusy(name: string, fn: () => Promise<void>) {
    try {
      setActionBusy(name);
      await fn();
    } finally {
      setActionBusy(null);
    }
  }

  const resolvedApi = base ? base : "(same-origin)";

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 selection:bg-[#1B74E4]/10">
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -top-48 left-1/2 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-[#1B74E4]/10 blur-3xl" />
        <div className="absolute bottom-[-140px] right-[-140px] h-[520px] w-[520px] rounded-full bg-slate-200/40 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-7xl px-6 py-12">
        <header className="mb-10 border-l-4 pl-6" style={{ borderColor: BRAND.blue }}>
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="font-mono text-[10px] font-bold uppercase tracking-[0.34em] text-slate-500">
                AION // Tessaris Intelligence
              </div>
              <h1 className="mt-2 text-4xl font-black tracking-tighter uppercase italic text-slate-900">
                Act 1: The Resonant Organism
              </h1>

              <div className="mt-4 font-mono text-[11px] text-slate-500">
                backend: <span className="text-slate-800">{resolvedApi}</span>
              </div>
              <div className="mt-1 font-mono text-[11px] text-slate-500">
                main: <span className="text-slate-800">{apiBase || "(same-origin)"}</span> · demo:{" "}
                <span className="text-slate-800">{demoBase}</span>
              </div>
            </div>

            <Chip tone={loading ? "neutral" : errSummary ? "bad" : "good"}>
              <span
                className={classNames(
                  "h-2 w-2 rounded-full",
                  loading ? "bg-slate-500" : errSummary ? "bg-rose-500" : "bg-emerald-500",
                  !loading && !errSummary && "animate-pulse"
                )}
              />
              <span>{loading ? "LINKING…" : errSummary ? "OFFLINE / DRIFT" : "FIELD_LOCKED"}</span>
            </Chip>
          </div>

          {!loading && Object.keys(errs).length ? (
            <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4">
              <div className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-rose-700">feed_errors</div>
              <div className="mt-2 space-y-1 font-mono text-[11px] text-rose-800">
                {Object.entries(errs).map(([k, v]) => (
                  <div key={k}>
                    <span className="uppercase">{k}</span>: {v}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </header>

        {/* Demo 00 (Homeostasis) */}
        <PillarSection
          id={demo00Meta.id}
          pillar={demo00Meta.pillar}
          title={demo00Meta.title}
          testName={demo00Meta.testName}
          copy={demo00Meta.copy}
          tone="dark"
          container={<PhaseClosureMonitorPanel homeostasis={homeostasis} mirror={mirror} />}
        />

        {/* Demo 04 Reflex */}
        <div className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-600">
                Demo Container 04
              </div>
              <div className="mt-1 text-xl font-black tracking-tight text-slate-900 uppercase italic">
                Reflex (Cognitive Grid)
              </div>
            </div>

            <div className="flex items-center gap-3">
              {ageChip(safeNum((reflex as any)?.age_ms) ?? ageFromLastUpdate(reflex))}
              <div className="font-mono text-[11px] text-slate-500">
                state: <span className="text-slate-800">{(reflex as any)?.state ? "online" : "offline"}</span>
              </div>
            </div>
          </div>

          <div className="mt-6">
            <Demo04ReflexGridPanel
              reflex={reflex as any}
              actionBusy={actionBusy}
              onReset={() =>
                runBusy("reflex_reset", () => postJson(joinUrl(demoBase, "/api/demo/reflex/reset"), { sessionId: "demo", namespace: "demo" }))
              }
              onStep={() =>
                runBusy("reflex_step", () => postJson(joinUrl(demoBase, "/api/demo/reflex/step"), { sessionId: "demo", namespace: "demo" }))
              }
              onRun={() =>
                runBusy("reflex_run", () => postJson(joinUrl(demoBase, "/api/demo/reflex/run"), { sessionId: "demo", namespace: "demo" }))
              }
            />
          </div>
        </div>

        {/* Demo 01 */}
        <PillarSection
          id={demo01Meta.id}
          pillar={demo01Meta.pillar}
          title={demo01Meta.title}
          testName={demo01Meta.testName}
          copy={demo01Meta.copy}
          container={
            <Demo01MetabolismPanel
              phi={phi as any}
              actionBusy={actionBusy}
              onReset={() => runBusy("phi_reset", () => postJson(joinUrl(demoBase, "/api/demo/phi/reset"), { sessionId: "demo", namespace: "demo" }))}
              onInjectEntropy={() => runBusy("phi_inject", () => postJson(joinUrl(demoBase, "/api/demo/phi/inject_entropy"), { sessionId: "demo", namespace: "demo" }))}
              onRecover={() => runBusy("phi_recover", () => postJson(joinUrl(demoBase, "/api/demo/phi/recover"), { sessionId: "demo", namespace: "demo" }))}
            />
          }
        />

        {/* Demo 02 (ADR) — ✅ fixed to main router endpoints */}
        <PillarSection
          id={demo02Meta.id}
          pillar={demo02Meta.pillar}
          title={demo02Meta.title}
          testName={demo02Meta.testName}
          copy={demo02Meta.copy}
          container={
            <Demo02AdrPanel
              adr={adr as any}
              actionBusy={actionBusy}
              onInject={() => runBusy("adr_inject", () => postJson(joinUrl(apiBase, "/api/adr/inject"), { amount: 0.33 }))}
              onRun={() => runBusy("adr_run", () => postJson(joinUrl(apiBase, "/api/adr/run"), {}))}
            />
          }
        />

        {/* Demo 03 */}
        <PillarSection
          id={demo03Meta.id}
          pillar={demo03Meta.pillar}
          title={demo03Meta.title}
          testName={demo03Meta.testName}
          copy={demo03Meta.copy}
          container={<Demo03HeartbeatPanel heartbeat={heartbeat as any} namespace="demo" />}
        />

        {/* Demo 05 */}
        <PillarSection
          id={demo05Meta.id}
          pillar={demo05Meta.pillar}
          title={demo05Meta.title}
          testName={demo05Meta.testName}
          copy={demo05Meta.copy}
          tone="dark"
          container={
            <Demo05AkgPanel
              akg={akg as any}
              actionBusy={actionBusy}
              onReset={() => runBusy("akg_reset", () => postJson(joinUrl(demoBase, "/api/demo/akg/reset"), { sessionId: "demo", namespace: "demo" }))}
              onStep={() => runBusy("akg_step", () => postJson(joinUrl(demoBase, "/api/demo/akg/step"), { sessionId: "demo", namespace: "demo" }))}
              onRun={() => runBusy("akg_run", () => postJson(joinUrl(demoBase, "/api/demo/akg/run?rounds=400"), { sessionId: "demo", namespace: "demo" }))}
            />
          }
        />

        {/* Demo 06 */}
        <PillarSection
          id={demo06Meta.id}
          pillar={demo06Meta.pillar}
          title={demo06Meta.title}
          testName={demo06Meta.testName}
          copy={demo06Meta.copy}
          tone="dark"
          container={<Demo06MirrorPanel mirror={mirror as any} />}
        />

        {/* AION Cognitive Dashboard */}
        <div className="mt-10">
          <AionCognitiveDashboard />
        </div>

        <footer className="mt-16 flex flex-col gap-3 border-t border-slate-200 pt-8 sm:flex-row sm:items-center sm:justify-between">
          <div className="font-mono text-[9px] uppercase tracking-[0.28em] text-slate-500">
            Tessaris Intelligence // Research Division // 2026
          </div>
          <div className="font-mono text-[9px] uppercase tracking-[0.28em] text-slate-500">Resonance_Engine</div>
        </footer>
      </div>
    </div>
  );
}