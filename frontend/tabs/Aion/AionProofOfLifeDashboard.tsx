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
type HomeostasisEnvelope = any; // GET /api/aion/dashboard payload (backend.main OR demo_bridge)
type MirrorEnvelope = any; // GET /api/mirror or /aion-demo/api/mirror payload

/* ---------------- URL resolution (supports BOTH main + demo mounts) ---------------- */

function stripSlash(s: string) {
  return (s || "").trim().replace(/\/+$/, "");
}

function normalizeHttpBase(raw: string) {
  let b = stripSlash(raw);
  if (!b) return "";
  // tolerate people pasting ".../api"
  b = b.replace(/\/api$/i, "");
  return b;
}

function resolveHttpBase(): string {
  const envDemo = normalizeHttpBase(process.env.NEXT_PUBLIC_AION_DEMO_HTTP_BASE || "");
  if (envDemo) return envDemo;

  const envAion = normalizeHttpBase(process.env.NEXT_PUBLIC_AION_API_BASE || "");
  if (envAion) return envAion;

  const legacy = normalizeHttpBase(process.env.NEXT_PUBLIC_API_URL || "");
  if (legacy) return legacy;

  if (typeof window !== "undefined") {
    const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    if (isLocal && window.location.port === "3000") return "http://127.0.0.1:8080";
    return ""; // same-origin
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
 *  - "/demo/..."  (mapped to "/api/demo/..."
 *  - "/aion/..."  (mapped to "/api/aion/..."
 */
function toApiPath(path: string) {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (p.startsWith("/api/")) return p;
  if (p.startsWith("/demo/")) return `/api${p}`;
  if (p.startsWith("/aion/")) return `/api${p}`;
  return `/api${p}`;
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

function safeStr(x: any): string | null {
  if (typeof x === "string") return x;
  if (x == null) return null;
  try {
    const s = String(x);
    return s.length ? s : null;
  } catch {
    return null;
  }
}

function num(x: any): number | null {
  const n = typeof x === "number" ? x : x != null ? Number(x) : NaN;
  return Number.isFinite(n) ? n : null;
}

function pickMetric(m: any, keys: string[]) {
  for (const k of keys) {
    if (m && Object.prototype.hasOwnProperty.call(m, k)) {
      const v = num(m[k]);
      if (v != null) return v;
    }
  }
  return null;
}

function pickStr(m: any, keys: string[]) {
  for (const k of keys) {
    if (m && Object.prototype.hasOwnProperty.call(m, k)) {
      const v = safeStr(m[k]);
      if (v != null) return v;
    }
  }
  return null;
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
    <section id={props.id} className="grid grid-cols-1 gap-8 py-10 lg:grid-cols-5 border-b border-slate-200 last:border-0">
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

/* ---------------- Data hook (polls all demos) ----------------
   ✅ FIX: auto-detect whether your feeds live under /api/* OR /aion-demo/api/*
   ✅ FIX: use the detected mount for POST actions, so buttons work again
*/

type DemoMount = "api" | "aion-demo" | null;

function useAionDemoData(pollMs = 500) {
  const httpBase = useMemo(() => resolveHttpBase(), []);

  const [homeostasis, setHomeostasis] = useState<HomeostasisEnvelope | null>(null);
  const [phi, setPhi] = useState<PhiBundle | null>(null);
  const [adr, setAdr] = useState<AdrBundle | null>(null);
  const [heartbeat, setHeartbeat] = useState<HeartbeatEnvelope | null>(null);
  const [reflex, setReflex] = useState<ReflexEnvelope | null>(null);
  const [akg, setAkg] = useState<AkgSnapshot | null>(null);
  const [mirror, setMirror] = useState<MirrorEnvelope | null>(null);

  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [demoMount, setDemoMount] = useState<DemoMount>(null);

  function u(path: string) {
    return joinUrl(httpBase, path);
  }

  async function firstOk<T>(urls: string[]): Promise<{ url: string; value: T } | null> {
    for (const url of urls) {
      try {
        const v = await fetchJson<T>(url);
        return { url, value: v };
      } catch {}
    }
    return null;
  }

  useEffect(() => {
    let cancelled = false;
    let t: any = null;

    const tick = async () => {
      try {
        const homeoUrls = [u("/api/aion/dashboard"), u("/aion-demo/api/aion/dashboard")];

        const phiUrls = [u("/api/phi"), u("/aion-demo/api/phi")];
        const adrUrls = [u("/api/adr"), u("/aion-demo/api/adr")];
        const hbUrls = [u("/api/heartbeat?namespace=demo"), u("/aion-demo/api/heartbeat?namespace=demo")];
        const reflexUrls = [u("/api/reflex"), u("/aion-demo/api/reflex")];
        const akgUrls = [u("/api/akg"), u("/aion-demo/api/akg")];
        const mirrorUrls = [u("/api/mirror"), u("/aion-demo/api/mirror")];

        const [homeoRes, phiRes, adrRes, hbRes, reflexRes, akgRes, mirrorRes] = await Promise.all([
          firstOk<HomeostasisEnvelope>(homeoUrls),
          firstOk<PhiBundle>(phiUrls),
          firstOk<AdrBundle>(adrUrls),
          firstOk<HeartbeatEnvelope>(hbUrls),
          firstOk<ReflexEnvelope>(reflexUrls),
          firstOk<AkgSnapshot>(akgUrls),
          firstOk<MirrorEnvelope>(mirrorUrls),
        ]);

        if (cancelled) return;

        if (homeoRes) setHomeostasis(homeoRes.value);
        if (phiRes) setPhi(phiRes.value);
        if (adrRes) setAdr(adrRes.value);
        if (hbRes) setHeartbeat(hbRes.value);
        if (reflexRes) setReflex(reflexRes.value);
        if (akgRes) setAkg(akgRes.value);
        if (mirrorRes) setMirror(mirrorRes.value);

        const demoHits = [phiRes, adrRes, hbRes, reflexRes, akgRes, mirrorRes].filter(Boolean) as Array<{ url: string }>;
        if (demoHits.length) {
          const anyAionDemo = demoHits.some((x) => x.url.includes("/aion-demo/api/"));
          setDemoMount(anyAionDemo ? "aion-demo" : "api");
        }

        const okCount = [homeoRes, phiRes, adrRes, hbRes, reflexRes, akgRes, mirrorRes].filter(Boolean).length;
        if (okCount === 0) setErr("All feeds offline (no /api/* or /aion-demo/api/* responders).");
        else setErr(null);
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
  }, [pollMs, httpBase]);

  // ✅ For POST actions: if demo is mounted at /aion-demo, base must be ".../aion-demo"
  const demoActionBase = useMemo(() => {
    if (demoMount === "aion-demo") return joinUrl(httpBase, "/aion-demo");
    // default to old working behavior (/api/*)
    return httpBase;
  }, [httpBase, demoMount]);

  return {
    homeostasis,
    phi,
    adr,
    heartbeat,
    reflex,
    akg,
    mirror,
    err,
    loading,
    httpBase,
    demoMount,
    demoActionBase,
  };
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

/* ---------------- Phase closure + cognition metrics (FIX your “—” panel) ---------------- */

type LatestMetrics = {
  event: string | null;
  term: string | null;
  sqi: number | null;
  rho: number | null;
  Ibar: number | null;
  dPhi: number | null;
  closure: number | null; // ⟲
  lock: boolean | null;
};

function extractHomeostasis(h: any) {
  const root = h?.homeostasis?.last ?? h?.homeostasis ?? h?.last ?? h?.state ?? h ?? {};
  const lock = typeof root?.locked === "boolean" ? root.locked : typeof h?.locked === "boolean" ? h.locked : null;

  const m = root?.metrics ?? root?.state?.metrics ?? root?.derived ?? root ?? {};

  const closure = pickMetric(m, ["⟲", "closure", "cycle", "homeostasis", "turns", "loop"]);
  const sqi_checkpoint = pickMetric(m, ["sqi_checkpoint", "SQI_checkpoint", "checkpoint_sqi"]);
  const age = safeNum(h?.age_ms) ?? ageFromLastUpdate(h);

  return { lock, closure, sqi_checkpoint, age, raw: root };
}

function extractLatestMetrics(args: {
  homeostasis: any | null;
  phi: any | null;
  adr: any | null;
  mirror: any | null;
}): LatestMetrics {
  const { homeostasis, phi, adr, mirror } = args;

  // Best effort sources
  const homeo = homeostasis ? extractHomeostasis(homeostasis) : { lock: null, closure: null, sqi_checkpoint: null, age: null, raw: null as any };

  const phiState = phi?.state ?? phi?.snapshot ?? phi ?? {};
  const adrState = adr?.state ?? adr?.snapshot ?? adr ?? {};
  const mirState = mirror?.state ?? mirror ?? {};

  // Event / term: mirror first, then ADR/phi/homeostasis
  const event = pickStr(mirState, ["event", "evt", "kind", "type"]) ?? pickStr(adrState, ["event", "evt", "kind", "type"]) ?? pickStr(phiState, ["event", "evt", "kind", "type"]) ?? null;
  const term = pickStr(mirState, ["term", "token", "label", "mode"]) ?? pickStr(adrState, ["term", "token", "label", "mode"]) ?? pickStr(phiState, ["term", "token", "label", "mode"]) ?? null;

  // SQI / ρ / Ī can show up anywhere; prefer explicit metric bags if present
  const mm = mirState?.metrics ?? mirState?.state?.metrics ?? {};
  const pm = phiState?.metrics ?? phiState?.state?.metrics ?? phiState ?? {};
  const am = adrState?.metrics ?? adrState?.state?.metrics ?? adrState ?? {};

  const sqi =
    pickMetric(mm, ["SQI", "sqi", "C", "coherence"]) ??
    pickMetric(pm, ["SQI", "sqi", "C", "coherence", "Φ_coherence", "Phi_coherence"]) ??
    pickMetric(am, ["SQI", "sqi", "C", "coherence"]) ??
    null;

  const rho =
    pickMetric(mm, ["ρ", "rho"]) ??
    pickMetric(pm, ["ρ", "rho"]) ??
    pickMetric(am, ["ρ", "rho"]) ??
    null;

  const Ibar =
    pickMetric(mm, ["Ī", "Ibar", "Ī", "I"]) ??
    pickMetric(pm, ["Ī", "Ibar", "Ī", "I"]) ??
    pickMetric(am, ["Ī", "Ibar", "Ī", "I"]) ??
    null;

  // ΔΦ: either explicit, or derived from (coh - ent) when available in phi
  const coh =
    pickMetric(phiState, ["Φ_coherence", "Phi_coherence", "coherence", "C"]) ??
    pickMetric(pm, ["Φ_coherence", "Phi_coherence", "coherence", "C"]) ??
    null;

  const ent =
    pickMetric(phiState, ["Φ_entropy", "Phi_entropy", "entropy"]) ??
    pickMetric(pm, ["Φ_entropy", "Phi_entropy", "entropy"]) ??
    null;

  const dPhi =
    pickMetric(phiState, ["ΔΦ", "dPhi", "delta_phi", "deltaPhi"]) ??
    (coh != null && ent != null ? coh - ent : null);

  return {
    event,
    term,
    sqi,
    rho,
    Ibar,
    dPhi,
    closure: homeo.closure,
    lock: homeo.lock,
  };
}

/* ---------------- Summary table (unchanged except existing phi-age fix) ---------------- */

function SummaryTable(props: {
  homeostasis?: any | null;
  adr?: any | null;
  phi?: any | null;
  akg?: any | null;
  mirror?: any | null;
  heartbeat?: any | null;
  reflex?: any | null;
}) {
  const homeoLast = props.homeostasis?.homeostasis?.last ?? props.homeostasis?.last ?? props.homeostasis?.state ?? null;
  const homeoLocked = typeof homeoLast?.locked === "boolean" ? homeoLast.locked : typeof props.homeostasis?.locked === "boolean" ? props.homeostasis.locked : null;

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

  const adrZone = String(props.adr?.derived?.zone || props.adr?.zone || "UNKNOWN");
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
        <div className="font-mono text-[10px] uppercase tracking-widest text-slate-500">Response to Stress • Autonomous Recovery</div>
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
          <Row pillar="Metabolism" comp="Φ-Field Calorimetry" target={`ΔΦ balance (coh=${coh ?? "—"}, ent=${ent ?? "—"})`} status={phiStatus} />
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
  const { homeostasis, phi, adr, heartbeat, reflex, akg, mirror, err, loading, httpBase, demoMount, demoActionBase } =
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

  const homeo = useMemo(() => (homeostasis ? extractHomeostasis(homeostasis) : null), [homeostasis]);

  // ✅ This drives the “Latest Metrics” block so it stops showing “—”
  const latest = useMemo(
    () => extractLatestMetrics({ homeostasis, phi, adr, mirror }),
    [homeostasis, phi, adr, mirror]
  );

  const closureOk = (latest.closure ?? 0) >= 0.975 && latest.lock === true;

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 selection:bg-[#1B74E4]/10">
      {/* subtle light brand glow */}
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
              <p className="mt-4 max-w-2xl text-sm font-medium leading-relaxed text-slate-600">
                These panels are “biological containers.” If a feed is stale, treat it as a genuine organismal failure mode (drift / disconnect), not a UI glitch.
              </p>

              <div className="mt-4 font-mono text-[11px] text-slate-500">
                API base: <span className="text-slate-800">{resolvedApi}</span>{" "}
                <span className="text-slate-400">(auto-detects /api/* vs /aion-demo/api/*)</span>
              </div>
              <div className="mt-1 font-mono text-[11px] text-slate-500">
                demo mount: <span className="text-slate-800">{demoMount ?? "detecting…"}</span> · action base:{" "}
                <span className="text-slate-800">{demoActionBase || "(same-origin)"}</span>
              </div>
            </div>

            <StatusBadge loading={loading} err={err} health={health} />
          </div>

          {err ? <div className="mt-4 font-mono text-[11px] uppercase tracking-widest text-rose-700">{err}</div> : null}
        </header>

        {/* ✅ FIXED Phase Closure Monitor (top-of-page, no more “Awaiting…”) */}
        <div className="mb-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-600">Phase Closure Monitor</div>
              <div className="mt-2 text-sm font-semibold text-slate-900">⟲ ≥ 0.975</div>
              <div className="mt-1 font-mono text-[11px] text-slate-500">
                source: <span className="text-slate-800">/api/aion/dashboard</span> (or{" "}
                <span className="text-slate-800">/aion-demo/api/aion/dashboard</span>)
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {homeo ? ageChip(homeo.age, 2000, 6000) : ageChip(null)}
              <Chip tone={latest.lock === true ? "good" : latest.lock === false ? "warn" : "warn"}>
                <span className={classNames("h-2 w-2 rounded-full", latest.lock === true ? "bg-emerald-500" : "bg-amber-500")} />
                <span>lock {latest.lock == null ? "—" : latest.lock ? "ON" : "OFF"}</span>
              </Chip>
              <Chip tone={closureOk ? "good" : "warn"}>
                <span className={classNames("h-2 w-2 rounded-full", closureOk ? "bg-emerald-500" : "bg-amber-500")} />
                <span>⟲ {latest.closure == null ? "—" : latest.closure.toFixed(3)}</span>
              </Chip>
            </div>
          </div>
        </div>

        {/* Demo 00 (Homeostasis / Auto-Lock) */}
        <PillarSection
          id={demo00Meta.id}
          pillar={demo00Meta.pillar}
          title={demo00Meta.title}
          testName={demo00Meta.testName}
          copy={demo00Meta.copy}
          tone="dark"
          container={<Demo00HomeostasisPanel homeostasis={homeostasis} />}
        />

        {/* Reflex (uses detected demoActionBase for POSTs) */}
        <div className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-600">Demo Container 04</div>
              <div className="mt-1 text-xl font-black tracking-tight text-slate-900 uppercase italic">Reflex (Cognitive Grid)</div>
              <div className="mt-2 font-mono text-[11px] uppercase tracking-widest text-slate-500">
                GET <span className="text-slate-800">{demoMount === "aion-demo" ? "/aion-demo/api/reflex" : "/api/reflex"}</span> · POST{" "}
                <span className="text-slate-800">
                  {demoMount === "aion-demo" ? "/aion-demo/api/demo/reflex/{reset,step,run}" : "/api/demo/reflex/{reset,step,run}"}
                </span>
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
              onReset={() => runBusy("reflex_reset", () => postApi(demoActionBase, "/demo/reflex/reset"))}
              onStep={() => runBusy("reflex_step", () => postApi(demoActionBase, "/demo/reflex/step"))}
              onRun={() => runBusy("reflex_run", () => postApi(demoActionBase, "/demo/reflex/run"))}
            />
          </div>

          <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-600">What this demonstrates</div>
            <p className="mt-2 text-sm leading-relaxed text-slate-600 font-medium">
              Reflex layer: novelty-seeking movement + immediate “stability breached” style self-report on danger nodes. Treat stalls as organismal drift, not UI glitch.
            </p>
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
              onReset={() => runBusy("reset", () => postApi(demoActionBase, "/demo/phi/reset"))}
              onInjectEntropy={() => runBusy("inject", () => postApi(demoActionBase, "/demo/phi/inject_entropy"))}
              onRecover={() => runBusy("recover", () => postApi(demoActionBase, "/demo/phi/recover"))}
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
              onInject={() => runBusy("adr_inject", () => postApi(demoActionBase, "/demo/adr/inject"))}
              onRun={() => runBusy("adr_run", () => postApi(demoActionBase, "/demo/adr/run"))}
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
              onReset={() => runBusy("akg_reset", () => postApi(demoActionBase, "/demo/akg/reset"))}
              onStep={() => runBusy("akg_step", () => postApi(demoActionBase, "/demo/akg/step"))}
              onRun={() =>
                runBusy("akg_run", () => postUrl(joinUrl(demoActionBase, "/api/demo/akg/run?rounds=400")))
              }
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

        {/* ✅ FIXED “Latest Metrics” block for the AION cognition section */}
        <div className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-600">AION Cognition Container</div>
              <div className="mt-1 text-xl font-black tracking-tight text-slate-900 uppercase italic">Latest Metrics</div>
              <div className="mt-2 font-mono text-[11px] uppercase tracking-widest text-slate-500">
                derived from: homeostasis + phi + adr + mirror (no WS required)
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Chip tone={latest.lock === true ? "good" : latest.lock === false ? "warn" : "warn"}>
                <span className={classNames("h-2 w-2 rounded-full", latest.lock === true ? "bg-emerald-500" : "bg-amber-500")} />
                <span>lock {latest.lock == null ? "—" : latest.lock ? "ON" : "OFF"}</span>
              </Chip>
              <Chip tone={closureOk ? "good" : "warn"}>
                <span className={classNames("h-2 w-2 rounded-full", closureOk ? "bg-emerald-500" : "bg-amber-500")} />
                <span>⟲ {latest.closure == null ? "—" : latest.closure.toFixed(3)}</span>
              </Chip>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Metric label="event" value={latest.event ?? "—"} />
            <Metric label="term" value={latest.term ?? "—"} />
            <Metric label="SQI" value={latest.sqi == null ? "—" : latest.sqi.toFixed(3)} />
            <Metric label="ρ" value={latest.rho == null ? "—" : latest.rho.toFixed(3)} />
            <Metric label="Ī" value={latest.Ibar == null ? "—" : latest.Ibar.toFixed(3)} />
            <Metric label="ΔΦ" value={latest.dPhi == null ? "—" : latest.dPhi.toFixed(3)} />
            <Metric label="⟲" value={latest.closure == null ? "—" : latest.closure.toFixed(3)} />
            <Metric label="Homeostasis ⟲" value={closureOk ? "1.00" : latest.closure == null ? "—" : (Math.min(1, Math.max(0, latest.closure / 0.975))).toFixed(2)} />
          </div>
        </div>

        {/* AION Cognitive Dashboard (kept) */}
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

function Metric(props: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-slate-500">{props.label}</div>
      <div className="mt-2 font-mono text-[14px] font-bold text-slate-900">{props.value}</div>
    </div>
  );
}