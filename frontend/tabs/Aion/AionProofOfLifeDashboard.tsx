// frontend/tabs/Aion/AionProofOfLifeDashboard.tsx
"use client";

import React, { useEffect, useMemo, useState } from "react";

// ✅ Prefer your shared types (keeps things consistent + tolerant)
import type { Envelope, PhiBundle, AdrBundle, HeartbeatEnvelope, ReflexEnvelope, AkgSnapshot } from "./demos/types";

// ✅ Existing demos
import { demo01Meta, Demo01MetabolismPanel } from "./demos/demo01_metabolism";
import { demo02Meta, Demo02AdrPanel } from "./demos/demo02_immune_adr";
import { demo03Meta, Demo03HeartbeatPanel } from "./demos/Demo03Heartbeat";
import { demo04Meta, Demo04ReflexGridPanel } from "./demos/demo04_reflex_grid";
import { demo05Meta, Demo05AkgPanel } from "./demos/demo5_akg_consolidation";

// ✅ Integrity + Mirror
import { demo00Meta, Demo00HomeostasisPanel } from "./demos/demo00_homeostasis_real";
import { demo06Meta, Demo06MirrorPanel } from "./demos/demo06_mirror_reflection";
import AionCognitiveDashboard from "./AionCognitiveDashboard";

/* ---------------- Types (tolerant; don’t block compilation) ---------------- */
type HomeostasisEnvelope = any; // GET /api/aion/dashboard payload (backend.main)
type MirrorEnvelope = any; // GET /aion-demo/api/mirror payload (demo_bridge)

/* ---------------- URL resolution (supports BOTH main + demo mounts) ---------------- */

function stripSlash(s: string) {
  return (s || "").trim().replace(/\/+$/, "");
}

function normalizeHttpBase(raw: string) {
  let b = stripSlash(raw);
  if (!b) return "";

  // tolerate people pasting ".../api" or ".../aion-demo"
  b = b.replace(/\/api$/i, "");
  b = b.replace(/\/aion-demo$/i, "");

  return b;
}

function resolveHttpBase(): string {
  // ✅ Single source of truth now
  const envDemo = normalizeHttpBase(process.env.NEXT_PUBLIC_AION_DEMO_HTTP_BASE || "");
  if (envDemo) return envDemo;

  // Local dev convenience
  if (typeof window !== "undefined") {
    const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    if (isLocal && window.location.port === "3000") return "http://127.0.0.1:8080";
    return ""; // same-origin fallback
  }

  return "";
}

function joinUrl(base: string, path: string) {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (!base) return p; // same-origin
  return stripSlash(base) + p;
}

/**
 * Accepts:
 *  - "/api/..."   (used as-is)
 *  - "/demo/..."  (mapped to "/api/demo/...")
 *  - "/aion/..."  (mapped to "/api/aion/...")
 */
function toApiPath(path: string) {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (p.startsWith("/api/")) return p;
  if (p.startsWith("/demo/")) return `/api${p}`; // /api/demo/...
  if (p.startsWith("/aion/")) return `/api${p}`; // /api/aion/...
  // default: assume already intended under /api
  return `/api${p}`;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });

  const ct = res.headers.get("content-type") || "";
  const text = await res.text().catch(() => "");

  if (!res.ok) {
    throw new Error(`${url} -> ${res.status} ${res.statusText}${text ? `: ${text.slice(0, 160)}` : ""}`);
  }

  // ✅ If BASE points at a frontend (Next) you'll get text/html 404 pages.
  if (!ct.includes("application/json")) {
    throw new Error(
      `${url} -> Expected JSON but got "${ct || "unknown"}". ` +
        `Your NEXT_PUBLIC_AION_DEMO_HTTP_BASE is probably pointing at the FRONTEND, not the API service.`
    );
  }

  return JSON.parse(text) as T;
}

async function postApi(base: string, path: string): Promise<void> {
  await fetchJson<any>(joinUrl(base, toApiPath(path)), { method: "POST" });
}

async function postUrl(url: string): Promise<void> {
  await fetchJson<any>(url, { method: "POST" });
}

/* ---------------- Small UI helpers ---------------- */

function classNames(...xs: Array<string | false | null | undefined>) {
  return xs.filter(Boolean).join(" ");
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

const BRAND = {
  blue: "#1B74E4",
};

/* ---------------- Chips ---------------- */

function Chip(props: { tone: "good" | "warn" | "bad" | "neutral"; children: React.ReactNode }) {
  const tone = props.tone;
  const cls =
    tone === "good"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : tone === "warn"
      ? "border-amber-200 bg-amber-50 text-amber-700"
      : tone === "bad"
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

  const stageInnerPad = tone === "dark" ? "" : "p-0";

  return (
    <section
      id={props.id}
      className="grid grid-cols-1 gap-8 py-10 lg:grid-cols-5 border-b border-slate-200 last:border-0"
    >
      <div className="lg:col-span-3">
        <div className={classNames(stage, stageInnerPad)}>{props.container}</div>
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

/* ---------------- Data hook (polls all demos) ---------------- */

function useAionDemoData(pollMs = 500) {
  const httpBase = useMemo(() => resolveHttpBase(), []);

  // ✅ Split bases:
  // - apiBase: backend.main root routes (/api/aion/dashboard)
  // - demoBase: demo_bridge mounted under /aion-demo (/aion-demo/api/*)
  const apiBase = useMemo(() => httpBase, [httpBase]);
  const demoBase = useMemo(
    () => (httpBase ? joinUrl(httpBase, "/aion-demo") : "/aion-demo"),
    [httpBase]
  );

  const [homeostasis, setHomeostasis] = useState<HomeostasisEnvelope | null>(null);
  const [phi, setPhi] = useState<PhiBundle | null>(null);
  const [adr, setAdr] = useState<AdrBundle | null>(null);
  const [heartbeat, setHeartbeat] = useState<HeartbeatEnvelope | null>(null);
  const [reflex, setReflex] = useState<ReflexEnvelope | null>(null);
  const [akg, setAkg] = useState<AkgSnapshot | null>(null);
  const [mirror, setMirror] = useState<MirrorEnvelope | null>(null);

  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let t: any = null;

    const tick = async () => {
      try {
        const urls = {
          // backend.main (root)
          homeo: joinUrl(apiBase, "/api/aion/dashboard"),

          // demo_bridge (mounted)
          phi: joinUrl(demoBase, "/api/phi"),
          adr: joinUrl(demoBase, "/api/adr"),
          hb: joinUrl(demoBase, "/api/heartbeat?namespace=demo"),
          reflex: joinUrl(demoBase, "/api/reflex"),
          akg: joinUrl(demoBase, "/api/akg"),
          mirror: joinUrl(demoBase, "/api/mirror"),
        };

        const results = await Promise.allSettled([
          fetchJson<HomeostasisEnvelope>(urls.homeo),
          fetchJson<PhiBundle>(urls.phi),
          fetchJson<AdrBundle>(urls.adr),
          fetchJson<HeartbeatEnvelope>(urls.hb),
          fetchJson<ReflexEnvelope>(urls.reflex),
          fetchJson<AkgSnapshot>(urls.akg),
          fetchJson<MirrorEnvelope>(urls.mirror),
        ]);

        if (cancelled) return;

        const [homeoRes, phiRes, adrRes, hbRes, reflexRes, akgRes, mirrorRes] = results;

        if (homeoRes.status === "fulfilled") setHomeostasis(homeoRes.value);
        if (phiRes.status === "fulfilled") setPhi(phiRes.value);
        if (adrRes.status === "fulfilled") setAdr(adrRes.value);
        if (hbRes.status === "fulfilled") setHeartbeat(hbRes.value);
        if (reflexRes.status === "fulfilled") setReflex(reflexRes.value);
        if (akgRes.status === "fulfilled") setAkg(akgRes.value);
        if (mirrorRes.status === "fulfilled") setMirror(mirrorRes.value);

        const okCount = results.filter((r) => r.status === "fulfilled").length;
        if (okCount === 0) {
          const errors: string[] = [];
          for (const r of results) if (r.status === "rejected") errors.push(r.reason?.message || String(r.reason));
          setErr(errors.length ? errors.join(" • ") : "All feeds offline");
        } else {
          setErr(null);
        }
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
  }, [pollMs, apiBase, demoBase]);

  return { homeostasis, phi, adr, heartbeat, reflex, akg, mirror, err, loading, httpBase, apiBase, demoBase };
}

/* ---------------- Status badge ---------------- */

function useDashboardHealth() {
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

  const tone: "neutral" | "bad" | "good" = loading ? "neutral" : err ? "bad" : "good";
  const label = loading ? "LINKING…" : err ? "OFFLINE / DRIFT" : "FIELD_LOCKED";

  const dotCls = tone === "good" ? "bg-emerald-500" : tone === "bad" ? "bg-rose-500" : "bg-slate-500";

  const borderCls =
    tone === "good"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : tone === "bad"
      ? "border-rose-200 bg-rose-50 text-rose-700"
      : "border-slate-200 bg-white text-slate-700";

  return (
    <div
      className={classNames(
        "flex items-center gap-3 rounded-full border px-4 py-2 font-mono text-[10px] font-bold tracking-[0.22em] uppercase shadow-sm",
        borderCls
      )}
      title={health.title}
    >
      <span className={classNames("h-2 w-2 rounded-full", dotCls, !loading && !err && "animate-pulse")} />
      <span>{label}</span>

      <span className="ml-1 hidden sm:inline-flex items-center gap-2 text-[10px] font-mono tracking-widest text-slate-500">
        <span className="h-3 w-px bg-slate-200" />
        <span>EVT:{health.events ?? "—"}</span>
        <span>AGE:{fmtAgeMs(health.age_ms)}</span>
      </span>
    </div>
  );
}

/* ---------------- Summary table ---------------- */

function ageFromLastUpdate(x: any): number | null {
  const lu = x?.last_update ?? x?.state?.last_update ?? x?.snapshot?.last_update;
  if (!lu) return null;
  const t = Date.parse(String(lu));
  if (!Number.isFinite(t)) return null;
  return Math.max(0, Date.now() - t);
}

function SummaryTable(props: {
  homeostasis?: any | null;
  adr?: any | null;
  phi?: any | null;
  akg?: any | null;
  mirror?: any | null;
  heartbeat?: any | null;
  reflex?: any | null;
}) {
  const homeoLast = props.homeostasis?.homeostasis?.last ?? props.homeostasis?.last ?? null;
  const homeoLocked = typeof homeoLast?.locked === "boolean" ? homeoLast.locked : null;

  const homeoStatus =
    homeoLocked === true ? (
      <Chip tone="good">
        <span className="h-2 w-2 rounded-full bg-emerald-500" />
        <span>LOCKED</span>
      </Chip>
    ) : homeoLocked === false ? (
      <Chip tone="warn">
        <span className="h-2 w-2 rounded-full bg-amber-500" />
        <span>UNLOCKED</span>
      </Chip>
    ) : (
      <Chip tone="warn">
        <span className="h-2 w-2 rounded-full bg-amber-500" />
        <span>NO_FEED</span>
      </Chip>
    );

  const adrZone = String(props.adr?.derived?.zone || "UNKNOWN");
  const adrStatus =
    adrZone === "GREEN" ? (
      <Chip tone="good">
        <span className="h-2 w-2 rounded-full bg-emerald-500" />
        <span>GREEN</span>
      </Chip>
    ) : adrZone === "YELLOW" ? (
      <Chip tone="warn">
        <span className="h-2 w-2 rounded-full bg-amber-500" />
        <span>YELLOW</span>
      </Chip>
    ) : adrZone === "RED" ? (
      <Chip tone="bad">
        <span className="h-2 w-2 rounded-full bg-rose-500" />
        <span>RED</span>
      </Chip>
    ) : (
      <Chip tone="warn">
        <span className="h-2 w-2 rounded-full bg-amber-500" />
        <span>NO_FEED</span>
      </Chip>
    );

  const hbAge = safeNum(props.heartbeat?.age_ms);
  const hbStatus = ageChip(hbAge);

  // ✅ FIX: phi producer often doesn't include age_ms; derive it from last_update instead.
  const phiAge = safeNum(props.phi?.age_ms) ?? ageFromLastUpdate(props.phi);
  const phiState = props.phi?.state || props.phi || {};
  const coh = phiState["Φ_coherence"] ?? phiState?.state?.["Φ_coherence"] ?? phiState?.Phi_coherence;
  const ent = phiState["Φ_entropy"] ?? phiState?.state?.["Φ_entropy"] ?? phiState?.Phi_entropy;
  const phiStatus = ageChip(phiAge);

  // mirror payload (your live BE): { ok, age_ms, state:{..., A:0.8337, ...} }
  const mirrorA = props.mirror?.A ?? props.mirror?.state?.A ?? props.mirror?.state?.derived?.A;
  const mirrorStatus =
    typeof mirrorA === "number" ? (
      mirrorA >= 0.9 ? (
        <Chip tone="good">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          <span>A={mirrorA.toFixed(3)}</span>
        </Chip>
      ) : (
        <Chip tone="warn">
          <span className="h-2 w-2 rounded-full bg-amber-500" />
          <span>A={mirrorA.toFixed(3)}</span>
        </Chip>
      )
    ) : (
      <Chip tone="warn">
        <span className="h-2 w-2 rounded-full bg-amber-500" />
        <span>NO_FEED</span>
      </Chip>
    );

  const reinf = props.akg?.reinforcements ?? props.akg?.snapshot?.reinforcements;
  const akgStatus =
    typeof reinf === "number" ? (
      reinf > 0 ? (
        <Chip tone="good">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          <span>+{reinf}</span>
        </Chip>
      ) : (
        <Chip tone="warn">
          <span className="h-2 w-2 rounded-full bg-amber-500" />
          <span>0</span>
        </Chip>
      )
    ) : (
      <Chip tone="warn">
        <span className="h-2 w-2 rounded-full bg-amber-500" />
        <span>NO_DATA</span>
      </Chip>
    );

  const reflexAge = safeNum(props.reflex?.age_ms);
  const reflexStatus = ageChip(reflexAge);

  return (
    <div className="mt-16 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between gap-6">
        <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-600">
          Act 1 Summary // Biological Containers
        </div>
        <div className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
          Response to Stress • Autonomous Recovery
        </div>
      </div>

      <div className="mt-6 overflow-hidden rounded-xl border border-slate-200">
        <div className="grid grid-cols-12 bg-slate-50 px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-slate-600">
          <div className="col-span-3">Pillar</div>
          <div className="col-span-4">UI Component</div>
          <div className="col-span-3">Target Metric</div>
          <div className="col-span-2 text-right">Status</div>
        </div>

        <div className="divide-y divide-slate-200 text-sm">
          <Row pillar="Integrity" comp="Phase Closure Monitor" target="⟲ ≥ 0.975 + sqi_checkpoint" status={homeoStatus} />
          <Row pillar="Awareness" comp="Mirror Reflection Log" target="Commentary + A ≥ 0.90" status={mirrorStatus} />
          <Row pillar="Stability" comp="RSI Stability Bar" target="RSI > 0.95 (Green)" status={adrStatus} />
          <Row pillar="Learning" comp="AKG Strength Delta" target="reinforcement > 0" status={akgStatus} />
          <Row
            pillar="Metabolism"
            comp="Φ-Field Calorimetry"
            target={`ΔΦ balance (coh=${coh ?? "—"}, ent=${ent ?? "—"})`}
            status={phiStatus}
          />
          <Row pillar="Reflex" comp="Cognitive Grid (Reflex)" target="fresh grid state" status={reflexStatus} />
          <Row pillar="Continuity" comp="Resonant Heartbeat" target="fresh Θ pulse" status={hbStatus} />
        </div>
      </div>
    </div>
  );
}

function Row(props: { pillar: string; comp: string; target: string; status: React.ReactNode }) {
  return (
    <div className="grid grid-cols-12 px-4 py-3 text-slate-800">
      <div className="col-span-3 font-semibold">{props.pillar}</div>
      <div className="col-span-4 font-mono text-[12px] text-slate-700">{props.comp}</div>
      <div className="col-span-3 text-slate-600">{props.target}</div>
      <div className="col-span-2 text-right font-mono text-[12px] uppercase tracking-wider">
        {props.status}
      </div>
    </div>
  );
}

/* ---------------- Page ---------------- */

export default function AionProofOfLifeDashboard() {
  const { homeostasis, phi, adr, heartbeat, reflex, akg, mirror, err, loading, httpBase, apiBase, demoBase } =
    useAionDemoData(500);

  const [actionBusy, setActionBusy] = useState<string | null>(null);

  const health = useDashboardHealth();
  useEffect(() => {
    health.updateFrom([homeostasis as any, phi as any, adr as any, heartbeat as any, reflex as any, akg as any, mirror as any], err, loading);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [homeostasis, phi, adr, heartbeat, reflex, akg, mirror, err, loading]);

  async function runBusy(name: string, fn: () => Promise<void>) {
    try {
      setActionBusy(name);
      await fn();
    } finally {
      setActionBusy(null);
    }
  }

  const footerRight = useMemo(() => {
    const candidates = [homeostasis as any, akg as any, reflex as any, heartbeat as any, adr as any, phi as any, mirror as any].filter(Boolean);
    for (const c of candidates) {
      const s = (c?.schema as string) || (c?.demo as string) || (c?.version as string) || (c?.derived?.phase as string) || null;
      if (s) return s;
    }
    return "Resonance_Engine";
  }, [homeostasis, akg, reflex, heartbeat, adr, phi, mirror]);

  const resolvedApi = useMemo(() => (httpBase ? httpBase : "(same-origin)"), [httpBase]);

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 selection:bg-[#1B74E4]/10">
      {/* subtle light brand glow */}
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -top-48 left-1/2 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-[#1B74E4]/10 blur-3xl" />
        <div className="absolute bottom-[-140px] right-[-140px] h-[520px] w-[520px] rounded-full bg-slate-200/40 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-7xl px-6 py-12">
        <header className="mb-14 border-l-4 pl-6" style={{ borderColor: BRAND.blue }}>
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="font-mono text-[10px] font-bold uppercase tracking-[0.34em] text-slate-500">AION // Tessaris Intelligence</div>
              <h1 className="mt-2 text-4xl font-black tracking-tighter uppercase italic text-slate-900">Act 1: The Resonant Organism</h1>
              <p className="mt-4 max-w-2xl text-sm font-medium leading-relaxed text-slate-600">
                These panels are “biological containers.” If a feed is stale, treat it as a genuine organismal failure mode (drift / disconnect), not a UI glitch.
              </p>

              <div className="mt-4 font-mono text-[11px] text-slate-500">
                API base: <span className="text-slate-800">{resolvedApi}</span>{" "}
                <span className="text-slate-400">(main: /api/* · demo: /aion-demo/api/*)</span>
              </div>
              <div className="mt-1 font-mono text-[11px] text-slate-500">
                main: <span className="text-slate-800">{apiBase || "(same-origin)"}</span> · demo:{" "}
                <span className="text-slate-800">{demoBase || "/aion-demo"}</span>
              </div>
            </div>

            <StatusBadge loading={loading} err={err} health={health} />
          </div>

          {err ? <div className="mt-4 font-mono text-[11px] uppercase tracking-widest text-rose-700">{err}</div> : null}
        </header>

        {/* Demo 00 (Homeostasis / Auto-Lock) - main backend */}
        <PillarSection
          id={demo00Meta.id}
          pillar={demo00Meta.pillar}
          title={demo00Meta.title}
          testName={demo00Meta.testName}
          copy={demo00Meta.copy}
          tone="dark"
          container={<Demo00HomeostasisPanel homeostasis={homeostasis} />}
        />

        {/* ✅ Reflex directly under Auto-Lock/Homeostasis (demo_bridge) */}
        <div className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-600">Demo Container 04</div>
              <div className="mt-1 text-xl font-black tracking-tight text-slate-900 uppercase italic">Reflex (Cognitive Grid)</div>
              <div className="mt-2 font-mono text-[11px] uppercase tracking-widest text-slate-500">
                GET <span className="text-slate-800">/aion-demo/api/reflex</span> · POST{" "}
                <span className="text-slate-800">/aion-demo/api/demo/reflex/{`{reset,step,run}`}</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {ageChip(safeNum((reflex as any)?.age_ms))}
              <div className="font-mono text-[11px] text-slate-500">
                state: <span className="text-slate-800">{(reflex as any)?.state ? "online" : "offline"}</span>
              </div>
            </div>
          </div>

          <div className="mt-6">
            <Demo04ReflexGridPanel
              reflex={reflex as any}
              actionBusy={actionBusy}
              onReset={() => runBusy("reflex_reset", () => postApi(demoBase, "/demo/reflex/reset"))}
              onStep={() => runBusy("reflex_step", () => postApi(demoBase, "/demo/reflex/step"))}
              onRun={() => runBusy("reflex_run", () => postApi(demoBase, "/demo/reflex/run"))}
            />
          </div>

          <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-600">What this demonstrates</div>
            <p className="mt-2 text-sm leading-relaxed text-slate-600 font-medium">
              Reflex layer: novelty-seeking movement + immediate “stability breached” style self-report on danger nodes. Treat stalls as organismal drift, not UI glitch.
            </p>
          </div>
        </div>

        {/* Demo 01 (demo_bridge) */}
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
              onReset={() => runBusy("reset", () => postApi(demoBase, "/demo/phi/reset"))}
              onInjectEntropy={() => runBusy("inject", () => postApi(demoBase, "/demo/phi/inject_entropy"))}
              onRecover={() => runBusy("recover", () => postApi(demoBase, "/demo/phi/recover"))}
            />
          }
        />

        {/* Demo 02 (demo_bridge) */}
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
              onInject={() => runBusy("adr_inject", () => postApi(demoBase, "/demo/adr/inject"))}
              onRun={() => runBusy("adr_run", () => postApi(demoBase, "/demo/adr/run"))}
            />
          }
        />

        {/* Demo 03 (demo_bridge) */}
        <PillarSection
          id={demo03Meta.id}
          pillar={demo03Meta.pillar}
          title={demo03Meta.title}
          testName={demo03Meta.testName}
          copy={demo03Meta.copy}
          container={<Demo03HeartbeatPanel heartbeat={heartbeat as any} namespace="demo" />}
        />

        {/* Demo 05 (demo_bridge) */}
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
              onReset={() => runBusy("akg_reset", () => postApi(demoBase, "/demo/akg/reset"))}
              onStep={() => runBusy("akg_step", () => postApi(demoBase, "/demo/akg/step"))}
              onRun={() => runBusy("akg_run", () => postUrl(joinUrl(demoBase, "/api/demo/akg/run?rounds=400")))}
            />
          }
        />

        {/* Demo 06 (demo_bridge) */}
        <PillarSection
          id={demo06Meta.id}
          pillar={demo06Meta.pillar}
          title={demo06Meta.title}
          testName={demo06Meta.testName}
          copy={demo06Meta.copy}
          tone="dark"
          container={<Demo06MirrorPanel mirror={mirror as any} />}
        />

        {/* AION Cognitive Dashboard (WS; already correct) */}
        <div className="mt-10">
          <AionCognitiveDashboard />
        </div>

        {/* Summary */}
        <SummaryTable homeostasis={homeostasis} adr={adr} phi={phi} akg={akg} mirror={mirror} heartbeat={heartbeat} reflex={reflex} />

        <footer className="mt-16 flex flex-col gap-3 border-t border-slate-200 pt-8 sm:flex-row sm:items-center sm:justify-between">
          <div className="font-mono text-[9px] uppercase tracking-[0.28em] text-slate-500">Tessaris Intelligence // Research Division // 2026</div>
          <div className="font-mono text-[9px] uppercase tracking-[0.28em] text-slate-500">{footerRight}</div>
        </footer>
      </div>
    </div>
  );
}