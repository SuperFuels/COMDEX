// frontend/tabs/Aion/AionProofOfLifeDashboard.tsx
"use client";

import React, { useEffect, useMemo, useState } from "react";

// ✅ Prefer your shared types (keeps things consistent + tolerant)
import type {
  Envelope,
  PhiBundle,
  AdrBundle,
  HeartbeatEnvelope,
  ReflexEnvelope,
  AkgSnapshot,
} from "./demos/types";

import { demo01Meta, Demo01MetabolismPanel } from "./demos/demo01_metabolism";
import { demo02Meta, Demo02AdrPanel } from "./demos/demo02_immune_adr";
import { demo03Meta, Demo03HeartbeatPanel } from "./demos/Demo03Heartbeat";
import { demo04Meta, Demo04ReflexGridPanel } from "./demos/demo04_reflex_grid";
import { demo05Meta, Demo05AkgPanel } from "./demos/demo5_akg_consolidation";

/* ---------------- API helpers (unchanged behavior) ---------------- */

function apiBase(): string | null {
  const raw = (process.env.NEXT_PUBLIC_API_URL || "").trim();
  if (!raw) return null;
  return raw.replace(/\/+$/, "");
}

function apiUrl(path: string): string {
  const base = apiBase();
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  if (!base) return `/api${cleanPath}`;
  const normalized = base.replace(/\/api$/i, "");
  return `${normalized}/api${cleanPath}`;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${url} -> ${res.status} ${res.statusText}${text ? `: ${text}` : ""}`);
  }
  return (await res.json()) as T;
}

async function post(path: string): Promise<void> {
  await fetchJson<any>(apiUrl(path), { method: "POST" });
}

// ✅ POST helper that supports querystrings without changing all callers
async function postUrl(url: string): Promise<void> {
  await fetchJson<any>(url, { method: "POST" });
}

/* ---------------- Small UI helpers ---------------- */

function classNames(...xs: Array<string | false | null | undefined>) {
  return xs.filter(Boolean).join(" ");
}

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function fmtAgeMs(ageMs?: number | null) {
  if (ageMs == null) return "—";
  const ms = Math.max(0, ageMs);
  if (ms < 1_000) return `${ms.toFixed(0)}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = s / 60;
  return `${m.toFixed(1)}m`;
}

function safeNum(x: any): number | null {
  const n = typeof x === "number" ? x : x != null ? Number(x) : NaN;
  return Number.isFinite(n) ? n : null;
}

/* ---------------- Brand-aligned section card ---------------- */

function PillarSection(props: {
  id: string;
  container: React.ReactNode;
  title: string;
  pillar: string;
  testName: string;
  copy: string;
}) {
  return (
    <section
      id={props.id}
      className="grid grid-cols-1 gap-8 py-10 lg:grid-cols-5 border-b border-white/5 last:border-0"
    >
      <div className="lg:col-span-3">{props.container}</div>

      <div className="lg:col-span-2 flex items-center">
        <div className="w-full rounded-2xl border border-slate-800/70 bg-white/5 p-6 backdrop-blur-sm shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-[#1B74E4]">
            {props.pillar}
          </div>

          <div className="mt-3 text-xl font-black tracking-tight text-white uppercase italic">
            {props.title}
          </div>

          <div className="mt-2 font-mono text-[11px] uppercase tracking-widest text-slate-400">
            ENGINE_MODE: <span className="text-slate-200">{props.testName}</span>
          </div>

          <div className="mt-6 h-px w-10 bg-[#1B74E4]/70" />

          <p className="mt-6 text-sm leading-relaxed text-slate-300 font-medium">{props.copy}</p>
        </div>
      </div>
    </section>
  );
}

/* ---------------- Data hook (polls all demos) ---------------- */

function useAionDemoData(pollMs = 500) {
  const [phi, setPhi] = useState<PhiBundle | null>(null);
  const [adr, setAdr] = useState<AdrBundle | null>(null);
  const [heartbeat, setHeartbeat] = useState<HeartbeatEnvelope | null>(null);
  const [reflex, setReflex] = useState<ReflexEnvelope | null>(null);
  const [akg, setAkg] = useState<AkgSnapshot | null>(null);

  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let t: any = null;

    const tick = async () => {
      try {
        const [phiRes, adrRes, hbRes, reflexRes, akgRes] = await Promise.allSettled([
          fetchJson<PhiBundle>(apiUrl("/phi")),
          fetchJson<AdrBundle>(apiUrl("/adr")),
          fetchJson<HeartbeatEnvelope>(apiUrl("/heartbeat?namespace=demo")),
          fetchJson<ReflexEnvelope>(apiUrl("/reflex")),
          fetchJson<AkgSnapshot>(apiUrl("/akg")),
        ]);

        if (cancelled) return;

        if (phiRes.status === "fulfilled") setPhi(phiRes.value);
        if (adrRes.status === "fulfilled") setAdr(adrRes.value);
        if (hbRes.status === "fulfilled") setHeartbeat(hbRes.value);
        if (reflexRes.status === "fulfilled") setReflex(reflexRes.value);
        if (akgRes.status === "fulfilled") setAkg(akgRes.value);

        const errors: string[] = [];
        if (phiRes.status === "rejected") errors.push(phiRes.reason?.message || String(phiRes.reason));
        if (adrRes.status === "rejected") errors.push(adrRes.reason?.message || String(adrRes.reason));
        if (hbRes.status === "rejected") errors.push(hbRes.reason?.message || String(hbRes.reason));
        if (reflexRes.status === "rejected") errors.push(reflexRes.reason?.message || String(reflexRes.reason));
        if (akgRes.status === "rejected") errors.push(akgRes.reason?.message || String(akgRes.reason));

        setErr(errors.length ? errors.join(" • ") : null);
      } catch (e: any) {
        if (!cancelled) setErr(e?.message || String(e));
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
  }, [pollMs]);

  return { phi, adr, heartbeat, reflex, akg, err, loading };
}

/* ---------------- Status badge (brand + telemetry-aware) ---------------- */

function useDashboardHealth() {
  // Best-effort telemetry derived from any Envelope-ish payload.
  const [events, setEvents] = useState<number | null>(null);
  const [age_ms, setAgeMs] = useState<number | null>(null);
  const [title, setTitle] = useState<string>("");

  return {
    events,
    age_ms,
    title,
    updateFrom(payloads: Array<Envelope<any> | null>, err: string | null, loading: boolean) {
      if (loading) {
        setTitle("Connecting to AION bridge…");
        return;
      }
      if (err) {
        setTitle(err);
        setEvents(null);
        setAgeMs(null);
        return;
      }

      const cands = payloads.filter(Boolean) as Array<Envelope<any>>;
      const ages = cands.map((p) => safeNum((p as any).age_ms)).filter((x): x is number => x != null);
      const evs = cands.map((p) => safeNum((p as any).events)).filter((x): x is number => x != null);

      const bestAge = ages.length ? Math.min(...ages) : null;
      const bestEvt = evs.length ? Math.max(...evs) : null;

      setAgeMs(bestAge);
      setEvents(bestEvt);

      const hints: string[] = [];
      if (bestEvt != null) hints.push(`events=${bestEvt}`);
      if (bestAge != null) hints.push(`age_ms=${bestAge}`);
      setTitle(hints.length ? `Telemetry: ${hints.join(" • ")}` : "Telemetry: (no envelope stats)");
    },
  };
}

function StatusBadge(props: { loading: boolean; err: string | null; health: ReturnType<typeof useDashboardHealth> }) {
  const { loading, err, health } = props;

  const state = loading
    ? { label: "LINKING…", tone: "neutral" as const }
    : err
    ? { label: "OFFLINE / DRIFT", tone: "bad" as const }
    : { label: "FIELD_LOCKED", tone: "good" as const };

  const classes =
    state.tone === "good"
      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
      : state.tone === "bad"
      ? "border-rose-500/40 bg-rose-500/10 text-rose-300"
      : "border-slate-500/30 bg-white/5 text-slate-200";

  const dot =
    state.tone === "good" ? "bg-emerald-400" : state.tone === "bad" ? "bg-rose-400" : "bg-slate-300";

  return (
    <div
      className={classNames(
        "flex items-center gap-3 rounded-full border px-4 py-2 font-mono text-[10px] font-bold tracking-[0.22em] uppercase transition-colors",
        classes
      )}
      title={health.title}
    >
      <span className={classNames("h-2 w-2 rounded-full", dot, !loading && !err && "animate-pulse")} />
      <span>{state.label}</span>

      {/* tiny telemetry chips */}
      <span className="ml-1 hidden sm:inline-flex items-center gap-2 text-[10px] font-mono tracking-widest text-white/60">
        <span className="h-3 w-px bg-white/10" />
        <span>EVT:{health.events ?? "—"}</span>
        <span>AGE:{fmtAgeMs(health.age_ms)}</span>
      </span>
    </div>
  );
}

/* ---------------- Summary Table (Act 1: Biological Containers) ---------------- */

function Row(props: { pillar: string; comp: string; target: string; status: React.ReactNode }) {
  return (
    <div className="grid grid-cols-12 px-4 py-3 text-slate-200">
      <div className="col-span-3 font-semibold">{props.pillar}</div>
      <div className="col-span-4 font-mono text-[12px] text-slate-300">{props.comp}</div>
      <div className="col-span-3 text-slate-400">{props.target}</div>
      <div className="col-span-2 text-right font-mono text-[12px] uppercase tracking-wider">{props.status}</div>
    </div>
  );
}

function SummaryTable(props: {
  homeostasis?: any | null;
  adr?: any | null;
  phi?: any | null;
  akg?: any | null;
  mirror?: any | null;
  heartbeat?: any | null;
}) {
  const adrZone = String(props.adr?.derived?.zone || "UNKNOWN");
  const hbAge = props.heartbeat?.age_ms;

  const phiState = props.phi?.state || props.phi || {};
  const coh = phiState["Φ_coherence"];
  const ent = phiState["Φ_entropy"];

  const fieldOk = (label: string) => (
    <span className="inline-flex items-center gap-2">
      <span className="h-2 w-2 rounded-full bg-emerald-400/90" />
      <span>{label}</span>
    </span>
  );
  const fieldWarn = (label: string) => (
    <span className="inline-flex items-center gap-2">
      <span className="h-2 w-2 rounded-full bg-amber-400/90" />
      <span>{label}</span>
    </span>
  );
  const fieldBad = (label: string) => (
    <span className="inline-flex items-center gap-2">
      <span className="h-2 w-2 rounded-full bg-rose-400/90" />
      <span>{label}</span>
    </span>
  );

  const adrStatus =
    adrZone === "GREEN" ? fieldOk("GREEN") : adrZone === "YELLOW" ? fieldWarn("YELLOW") : fieldBad("RED");

  const hbStatus =
    typeof hbAge === "number"
      ? hbAge < 2000
        ? fieldOk(`PULSE ${hbAge}ms`)
        : hbAge < 6000
          ? fieldWarn(`PULSE ${hbAge}ms`)
          : fieldBad(`STALE ${hbAge}ms`)
      : fieldWarn("NO_PULSE");

  // Replace once REAL endpoint exists:
  const homeoStatus = props.homeostasis?.locked ? fieldOk("LOCKED") : fieldWarn("UNLOCKED");

  // Mirror + AKG optional until endpoints are live
  const mirrorA = props.mirror?.A ?? props.mirror?.state?.A;
  const mirrorStatus =
    typeof mirrorA === "number"
      ? mirrorA >= 0.75
        ? fieldOk(`A=${mirrorA}`)
        : fieldWarn(`A=${mirrorA}`)
      : fieldWarn("NO_FEED");

  const reinf = props.akg?.reinforcements ?? props.akg?.snapshot?.reinforcements;
  const akgStatus =
    typeof reinf === "number" ? (reinf > 0 ? fieldOk(`+${reinf}`) : fieldWarn("0")) : fieldWarn("NO_DATA");

  return (
    <div className="mt-16 rounded-2xl border border-white/5 bg-white/3 p-6 backdrop-blur-sm">
      <div className="flex items-center justify-between">
        <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-500">
          Act 1 Summary // Biological Containers
        </div>
        <div className="font-mono text-[10px] uppercase tracking-widest text-slate-600">
          Response to Stress • Autonomous Recovery
        </div>
      </div>

      <div className="mt-6 overflow-hidden rounded-xl border border-white/5">
        <div className="grid grid-cols-12 bg-white/2 px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-slate-500">
          <div className="col-span-3">Pillar</div>
          <div className="col-span-4">UI Component</div>
          <div className="col-span-3">Target Metric</div>
          <div className="col-span-2 text-right">Status</div>
        </div>

        <div className="divide-y divide-white/5 text-sm">
          <Row pillar="Integrity" comp="Phase Closure Monitor" target="π_s = 2π" status={homeoStatus} />
          <Row
            pillar="Awareness"
            comp="Mirror Reflection Log"
            target="Linguistic Accuracy > 90%"
            status={mirrorStatus}
          />
          <Row pillar="Stability" comp="RSI Stability Bar" target="RSI > 0.95 (Green)" status={adrStatus} />
          <Row pillar="Learning" comp="AKG Strength Delta" target="+12% reinforcement" status={akgStatus} />
          <Row
            pillar="Metabolism"
            comp="Φ-Field Calorimetry"
            target={`ΔΦ balance (coh=${coh ?? "?"}, ent=${ent ?? "?"})`}
            status={fieldOk("LIVE")}
          />
          <Row pillar="Reflex" comp="Drift Repair Pulse" target="Trigger at RSI < 0.6" status={adrStatus} />
          <Row pillar="Continuity" comp="Resonant Heartbeat" target="60s periodic pulse" status={hbStatus} />
        </div>
      </div>
    </div>
  );
}

/* ---------------- Page ---------------- */

export default function AionProofOfLifeDashboard() {
  const { phi, adr, heartbeat, reflex, akg, err, loading } = useAionDemoData(500);

  // shared busy flag: demo panels only read this to disable buttons + show labels
  const [actionBusy, setActionBusy] = useState<string | null>(null);

  const health = useDashboardHealth();
  useEffect(() => {
    health.updateFrom([phi as any, adr as any, heartbeat as any, reflex as any, akg as any], err, loading);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phi, adr, heartbeat, reflex, akg, err, loading]);

  async function runBusy(name: string, fn: () => Promise<void>) {
    try {
      setActionBusy(name);
      await fn();
    } finally {
      setActionBusy(null);
    }
  }

  const footerRight = useMemo(() => {
    // best effort: show a phase string if present in any demo snapshot
    const candidates = [akg as any, reflex as any, heartbeat as any, adr as any, phi as any].filter(Boolean);
    for (const c of candidates) {
      const s =
        (c?.schema as string) ||
        (c?.demo as string) ||
        (c?.version as string) ||
        (c?.derived?.phase as string) ||
        null;
      if (s) return s;
    }
    return "Resonance_Engine";
  }, [akg, reflex, heartbeat, adr, phi]);

  return (
    <div className="min-h-screen bg-[#0F172A] text-white selection:bg-[#1B74E4]/30">
      {/* subtle brand glow */}
      <div className="pointer-events-none fixed inset-0 opacity-60">
        <div className="absolute -top-40 left-1/2 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-[#1B74E4]/20 blur-3xl" />
        <div className="absolute bottom-0 right-[-140px] h-[420px] w-[420px] rounded-full bg-white/5 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-7xl px-6 py-12">
        <header className="mb-14 border-l-4 border-[#1B74E4] pl-6">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="font-mono text-[10px] font-bold uppercase tracking-[0.34em] text-slate-500">
                AION // Tessaris Intelligence
              </div>
              <h1 className="mt-2 text-4xl font-black tracking-tighter uppercase italic">
                Act 1: The Resonant Organism
              </h1>
              <p className="mt-4 max-w-2xl text-sm font-medium leading-relaxed text-slate-400">
                Live monitoring of AION’s physiological + cognitive field. Stabilizing memory recall, reflex drift, and
                triplet reinforcement across the runtime.
              </p>
            </div>

            <StatusBadge loading={loading} err={err} health={health} />
          </div>

          {err ? (
            <div className="mt-4 font-mono text-[11px] uppercase tracking-widest text-rose-300/80">{err}</div>
          ) : null}
        </header>

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
              onReset={() => runBusy("reset", () => post("/demo/phi/reset"))}
              onInjectEntropy={() => runBusy("inject", () => post("/demo/phi/inject_entropy"))}
              onRecover={() => runBusy("recover", () => post("/demo/phi/recover"))}
            />
          }
        />

        {/* Demo 02 */}
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
              onInject={() => runBusy("adr_inject", () => post("/demo/adr/inject"))}
              onRun={() => runBusy("adr_run", () => post("/demo/adr/run"))}
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

        {/* Demo 04 */}
        <PillarSection
          id={demo04Meta.id}
          pillar={demo04Meta.pillar}
          title={demo04Meta.title}
          testName={demo04Meta.testName}
          copy={demo04Meta.copy}
          container={
            <Demo04ReflexGridPanel
              reflex={reflex as any}
              actionBusy={actionBusy}
              onReset={() => runBusy("reflex_reset", () => post("/demo/reflex/reset"))}
              onStep={() => runBusy("reflex_step", () => post("/demo/reflex/step"))}
              onRun={() => runBusy("reflex_run", () => post("/demo/reflex/run"))}
            />
          }
        />

        {/* Demo 05 */}
        <PillarSection
          id={demo05Meta.id}
          pillar={demo05Meta.pillar}
          title={demo05Meta.title}
          testName={demo05Meta.testName}
          copy={demo05Meta.copy}
          container={
            <Demo05AkgPanel
              akg={akg as any}
              actionBusy={actionBusy}
              onReset={() => runBusy("akg_reset", () => post("/demo/akg/reset"))}
              onStep={() => runBusy("akg_step", () => post("/demo/akg/step"))}
              onRun={() => runBusy("akg_run", () => postUrl(apiUrl("/demo/akg/run?rounds=400")))}
            />
          }
        />

        {/* ✅ Summary Table (bottom of Act 1 list) */}
        <SummaryTable
          homeostasis={null /* wire when REAL endpoint exists */}
          adr={adr}
          phi={phi}
          akg={akg}
          mirror={null /* wire when /api/mirror exists */}
          heartbeat={heartbeat}
        />

        <footer className="mt-16 flex flex-col gap-3 border-t border-white/5 pt-8 sm:flex-row sm:items-center sm:justify-between">
          <div className="font-mono text-[9px] uppercase tracking-[0.28em] text-slate-600">
            Tessaris Intelligence // Research Division // 2026
          </div>
          <div className="font-mono text-[9px] uppercase tracking-[0.28em] text-slate-600">{footerRight}</div>
        </footer>
      </div>
    </div>
  );
}