"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * RQC AWARENESS HORIZON — v0.7 (FIXED)
 *
 * Goals:
 * 1) Correct mapping: Φ is NOT ψ, and entropy is NOT guessed from κ unless we truly have no entropy signal.
 * 2) Stable event stream: throttle telemetry logging + keep a rolling history for the graph.
 * 3) Manifold bars: derived from coherence (C) only; never from Φ/ψ.
 * 4) Works with payload variability (flat / nested / phi object).
 *
 * Expected live feed (from your stream):
 *  - SQI or coherence is the "C" value (0..1)
 *  - Φ (awareness) may be absent; if absent, we derive Φ from C (your current demo does that)
 *  - Entropy is Ī / Ibar (0..1) if provided; else derive from 1-C (NOT κ)
 *  - ψ (wave presence) is ψ if present; else use ρ if present; else derive from C
 */

const SESSION_ID = "a99acc96-acde-48d5-9b6d-d2f434536d5b";

const STALE_MS = 2_500;
const TELEMETRY_LOG_EVERY_MS = 1_000; // throttle to 1 log / sec
const HISTORY_LEN = 64; // graph history points

type Mode = "SIM" | "LIVE" | "LIVE_STALE";
type Status = "STABLE" | "ALIGNING" | "CRITICAL_DRIFT" | "NO_FEED";
type LogItem = { t: number; msg: string; kind: "info" | "warn" | "ok" | "bad" };

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

function safeUrl(u: string) {
  try {
    return new URL(u);
  } catch {
    return null;
  }
}

function num(x: any): number | null {
  const n = typeof x === "number" ? x : x != null ? Number(x) : NaN;
  return Number.isFinite(n) ? n : null;
}

function hasOwn(o: any, k: string) {
  return o && Object.prototype.hasOwnProperty.call(o, k);
}

function pickMetric(m: any, keys: string[]) {
  for (const k of keys) {
    if (hasOwn(m, k)) {
      const v = num(m[k]);
      if (v != null) return v;
    }
  }
  return null;
}

/**
 * Normalize incoming message to a stable set of signals.
 * Returns raw candidates; we finalize/derive in applyTelemetry().
 */
function normalize(msg: any) {
  const root = msg ?? {};
  const m = root?.metrics ?? root?.state?.metrics ?? root;
  const phiObj = root?.phi ?? root?.state?.phi ?? root?.state?.Φ ?? {};

  // Primary coherence / quality signal:
  // - demo shows SQI and ρ same value; that's your coherence (C)
  const C =
    pickMetric(phiObj, ["Φ_coherence", "phi_coherence", "coherence", "C"]) ??
    pickMetric(m, ["C", "coherence", "SQI", "sqi", "ρ", "rho"]);

  // Awareness:
  // - use Φ if actually provided, else derive from C (per your design)
  const Phi =
    pickMetric(m, ["Φ", "phi"]) ??
    pickMetric(phiObj, ["Φ", "phi"]) ??
    null;

  // Entropy:
  // - prefer explicit Φ_entropy or Ibar (Ī) if present
  const entropy =
    pickMetric(phiObj, ["Φ_entropy", "phi_entropy", "entropy", "E"]) ??
    pickMetric(m, ["Ī", "Ibar", "Ī", "iota", "entropy", "E"]);

  // Wave presence (ψ):
  // - prefer ψ; else ρ; else derive from C later
  const psi = pickMetric(m, ["ψ", "psi", "presence"]) ?? pickMetric(m, ["ρ", "rho"]);

  // Curvature & temporal are optional; don't invent them
  const kappa = pickMetric(m, ["κ", "kappa", "curvature"]);
  const T = pickMetric(m, ["T", "temp", "temporal", "time"]);

  const rho = pickMetric(m, ["ρ", "rho"]);
  const Ibar = pickMetric(m, ["Ī", "Ibar", "Ī", "iota"]);

  const src = typeof root?.source === "string" ? root.source : null;
  return { psi, kappa, T, Phi, C, entropy, rho, Ibar, src };
}

/**
 * If you set NEXT_PUBLIC_API_BASE to:
 *   https://...run.app/api
 * we derive origin as:
 *   https://...run.app
 */
function resolveOrigin(): string {
  const raw = (
    process.env.NEXT_PUBLIC_AION_DEMO_HTTP_BASE ||
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_AION_API_BASE ||
    process.env.NEXT_PUBLIC_API_BASE ||
    ""
  ).trim();

  const u = raw ? safeUrl(raw) : null;
  if (u) {
    u.pathname = "/";
    u.search = "";
    u.hash = "";
    return u.toString().replace(/\/+$/, "");
  }

  if (typeof window !== "undefined") return window.location.origin;
  return "";
}

function pickRqcWsUrl() {
  const normalizeWs = (raw: string) => {
    let s = (raw || "").trim().replace(/\/+$/, "");
    if (!s) return "";
    if (s.startsWith("https://")) s = "wss://" + s.slice("https://".length);
    else if (s.startsWith("http://")) s = "ws://" + s.slice("http://".length);
    return s;
  };

  // Explicit override:
  const raw = normalizeWs(process.env.NEXT_PUBLIC_RQC_WS || "");
  if (raw) return raw;

  const demoBase =
    (process.env.NEXT_PUBLIC_AION_DEMO_BASE ||
      process.env.NEXT_PUBLIC_AION_DEMO_HTTP_BASE ||
      "").trim();

  if (demoBase) {
    const http = demoBase.replace(/\/+$/, "");
    const wsRoot = normalizeWs(http);
    if (http.endsWith("/aion-demo")) return `${wsRoot}/ws/aion-demo`;
    return `${wsRoot}/aion-demo/ws/aion-demo`;
  }

  const origin = resolveOrigin();
  if (origin) {
    const wsRoot = normalizeWs(origin);
    return `${wsRoot}/aion-demo/ws/aion-demo`;
  }

  if (typeof window !== "undefined") {
    const isLocal =
      window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    if (isLocal) return "ws://127.0.0.1:8080/aion-demo/ws/aion-demo";
  }

  return "";
}

function pickAionDemoBase() {
  const origin = resolveOrigin();
  return origin ? `${origin}/aion-demo` : "";
}

async function postJson(url: string, body: any, timeoutMs = 8000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body ?? {}),
      signal: ctrl.signal,
    });
    const txt = await r.text();
    let json: any = null;
    try {
      json = txt ? JSON.parse(txt) : null;
    } catch {
      json = { _nonJson: true, _text: txt.slice(0, 500) };
    }
    return { ok: r.ok, status: r.status, json };
  } finally {
    clearTimeout(t);
  }
}

export default function RQCAwarenessDemo() {
  // Live slots (truth):
  const [psi, setPsi] = useState<number | null>(null);
  const [kappa, setKappa] = useState<number | null>(null);
  const [T, setT] = useState<number | null>(null);

  const [entropy, setEntropy] = useState<number | null>(null); // E
  const [phi, setPhi] = useState<number | null>(null); // Φ
  const [coherence, setCoherence] = useState<number | null>(null); // C / SQI

  const [status, setStatus] = useState<Status>("NO_FEED");
  const [manifoldSync, setManifoldSync] = useState<number[] | null>(null);

  // Graph history (fixed)
  const [phiHist, setPhiHist] = useState<number[]>([]);
  const [entHist, setEntHist] = useState<number[]>([]);

  const [isInjecting, setIsInjecting] = useState(false);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [running, setRunning] = useState(false);

  const wsUrl = useMemo(() => pickRqcWsUrl(), []);
  const aionDemoBase = useMemo(() => pickAionDemoBase(), []);

  const wsRef = useRef<WebSocket | null>(null);
  const [liveConnected, setLiveConnected] = useState(false);
  const [lastLiveAt, setLastLiveAt] = useState<number>(0);

  const lastTelemetryLogAtRef = useRef(0);

  // SIM refs
  const entropyRef = useRef<number>(0.15);
  const phiRef = useRef<number>(0.64);
  const cohRef = useRef<number>(0.64);

  // Last-known refs for stable derivation
  const lastStateRef = useRef<{ e: number; c: number; phi: number; psi: number } | null>(null);

  const addLog = (msg: string, kind: LogItem["kind"] = "info") => {
    setLogs((prev) => [{ t: Date.now(), msg, kind }, ...prev].slice(0, 10));
  };

  const computeStatus = (e: number, c: number): Status => {
    if (e >= 0.6 || c <= 0.35) return "CRITICAL_DRIFT";
    if (e >= 0.12 || c < 0.85) return "ALIGNING";
    return "STABLE";
  };

  const mode: Mode = useMemo(() => {
    if (!wsUrl) return "SIM";
    if (!liveConnected) return "LIVE_STALE";
    const age = lastLiveAt ? Date.now() - lastLiveAt : Infinity;
    return age <= STALE_MS ? "LIVE" : "LIVE_STALE";
  }, [wsUrl, liveConnected, lastLiveAt]);

  const liveIsFresh = mode === "LIVE";

  // Derived indices
  const resonanceIndex = useMemo(() => {
    if (entropy == null) return null;
    return clamp01(1 - entropy * 0.2);
  }, [entropy]);

  const stabilityIndex = useMemo(() => {
    if (phi == null) return null;
    return clamp01(phi * 0.95);
  }, [phi]);

  const closureOk = useMemo(() => {
    if (phi == null || coherence == null || entropy == null) return false;
    return phi >= 0.92 && coherence >= 0.92 && entropy <= 0.08;
  }, [phi, coherence, entropy]);

  const buildProofJsonLd = () => {
    const payload = {
      "@context": {
        "@vocab": "https://tessaris.ai/rfc#",
        sessionId: "sessionId",
        proofType: "proofType",
        statement: "statement",
        metrics: "metrics",
        derived: "derived",
        generatedAt: "generatedAt",
      },
      "@type": "RQCAwarenessClosureProof",
      sessionId: SESSION_ID,
      proofType: "Awareness Horizon (Φ) Phase Closure",
      statement:
        "Awareness loop converged: Φ stabilized while entropy collapsed; phase closure achieved without leakage.",
      metrics: { psi, kappa, T, entropy, phi, coherence, manifoldSync },
      derived: { resonanceIndex, stabilityIndex, status, mode, wsUrl: wsUrl || null, aionDemoBase },
      generatedAt: new Date().toISOString(),
    };
    return JSON.stringify(payload, null, 2);
  };

  const downloadProof = () => {
    const json = buildProofJsonLd();
    const blob = new Blob([json], { type: "application/ld+json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rqc_awareness_proof_${SESSION_ID.slice(0, 8)}.jsonld`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    addLog("[Certificate] JSON-LD exported → Phase Closure Certificate emitted.", "ok");
  };

  const reset = () => {
    setPsi(null);
    setKappa(null);
    setT(null);
    setEntropy(null);
    setPhi(null);
    setCoherence(null);
    setManifoldSync(null);
    setPhiHist([]);
    setEntHist([]);
    setStatus("NO_FEED");
    setIsInjecting(false);
    setLogs([]);
    lastStateRef.current = null;

    entropyRef.current = 0.15;
    phiRef.current = 0.64;
    cohRef.current = 0.64;

    addLog("[System] Reset: Awareness Horizon re-armed.", "info");
  };

  const applyTelemetry = (nm: ReturnType<typeof normalize>) => {
    // Coherence: MUST come from C/SQI/rho (not psi)
    const c =
      nm.C != null
        ? clamp01(nm.C)
        : lastStateRef.current?.c ?? null;

    // Entropy: prefer explicit; else use Ibar; else derive from (1 - C)
    let e: number | null =
      nm.entropy != null
        ? clamp01(nm.entropy)
        : nm.Ibar != null
        ? clamp01(nm.Ibar)
        : null;

    if (e == null && c != null) e = clamp01(1 - c);

    // Phi: prefer explicit Φ; else derive from C (your demo behaviour)
    let p: number | null = nm.Phi != null ? clamp01(nm.Phi) : null;
    if (p == null && c != null) p = c;

    // Psi: prefer ψ; else ρ; else derive from C (soft)
    let ps: number | null = nm.psi != null ? clamp01(nm.psi) : null;
    if (ps == null && nm.rho != null) ps = clamp01(nm.rho);
    if (ps == null && c != null) ps = clamp01(0.15 + c * 0.35);

    // Only set optional slots if provided
    if (nm.kappa != null) setKappa(nm.kappa);
    if (nm.T != null) setT(nm.T);

    if (ps != null) setPsi(ps);
    if (c != null) setCoherence(c);
    if (p != null) setPhi(p);
    if (e != null) setEntropy(e);

    // History for graph (smooth, correct)
    if (p != null) {
      setPhiHist((prev) => {
        const next = [...prev, p];
        return next.length > HISTORY_LEN ? next.slice(next.length - HISTORY_LEN) : next;
      });
    }
    if (e != null) {
      setEntHist((prev) => {
        const next = [...prev, e];
        return next.length > HISTORY_LEN ? next.slice(next.length - HISTORY_LEN) : next;
      });
    }

    // Manifold bars derive from coherence only (0..100)
    if (c != null) {
      const base = clamp(c * 100, 0, 100);
      setManifoldSync([0, 1, 2, 3].map((i) => clamp(base + i * 0.2, 0, 100)));
    }

    // Status uses (entropy, coherence)
    const eUsed = e ?? lastStateRef.current?.e ?? 0.5;
    const cUsed = c ?? lastStateRef.current?.c ?? 0.5;
    const s = computeStatus(eUsed, cUsed);
    setStatus(s);

    lastStateRef.current = {
      e: eUsed,
      c: cUsed,
      phi: p ?? lastStateRef.current?.phi ?? cUsed,
      psi: ps ?? lastStateRef.current?.psi ?? 0.0,
    };

    // Throttled event stream line (stable)
    const now = Date.now();
    if (now - lastTelemetryLogAtRef.current >= TELEMETRY_LOG_EVERY_MS) {
      lastTelemetryLogAtRef.current = now;
      const src = nm.src ? ` src=${nm.src}` : "";
      addLog(
        `[Telemetry] ψ=${ps != null ? ps.toFixed(5) : "—"} κ=${nm.kappa != null ? nm.kappa : "—"} T=${nm.T != null ? nm.T : "—"} Φ=${p != null ? p.toFixed(4) : "—"} C=${c != null ? c.toFixed(4) : "—"} E=${e != null ? e.toFixed(4) : "—"}${src}`,
        s === "CRITICAL_DRIFT" ? "warn" : "info"
      );
      if (c != null && (nm.rho != null || nm.Ibar != null)) {
        addLog(
          `[RQC] SQI=${c.toFixed(4)} ρ=${nm.rho != null ? nm.rho.toFixed(4) : "—"} Ī=${
            nm.Ibar != null ? nm.Ibar.toFixed(4) : "—"
          }`,
          "info"
        );
      }
    }
  };

  const injectEntropy = async () => {
    setIsInjecting(true);
    try {
      const r = await postJson(`${aionDemoBase}/api/demo/inject_entropy`, { sessionId: SESSION_ID });
      if (r.ok) addLog(`[AION_DEMO] Inject triggered (${aionDemoBase}/api/demo/inject_entropy)`, "warn");
      else {
        const r2 = await postJson(`${aionDemoBase}/api/demo/phi/inject_entropy`, { sessionId: SESSION_ID });
        if (r2.ok) addLog(`[AION_DEMO] Φ entropy injected (demo bridge).`, "warn");
        else throw new Error("demo bridge not available");
      }
    } catch {
      // SIM fallback
      entropyRef.current = 0.85;
      phiRef.current = 0.32;
      cohRef.current = 0.32;

      setEntropy(0.85);
      setPhi(0.32);
      setCoherence(0.32);
      setStatus("CRITICAL_DRIFT");
      addLog("[SIM] External Entropy Injected: Phase drift detected.", "warn");
    } finally {
      window.setTimeout(() => setIsInjecting(false), 900);
    }
  };

  // LIVE MODE
  useEffect(() => {
    if (!running) return;
    if (!wsUrl) return;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setLiveConnected(true);
      addLog(`[RQC_LIVE] OPEN → ${wsUrl}`, "ok");
      try {
        ws.send(JSON.stringify({ type: "hello", client: "RQCAwarenessDemo", sessionId: SESSION_ID }));
      } catch {}
    };

    ws.onclose = (ev) => {
      setLiveConnected(false);
      addLog(`[RQC_LIVE] CLOSE code=${ev.code} reason=${ev.reason || "—"}`, "warn");
    };

    ws.onerror = (ev) => {
      setLiveConnected(false);
      addLog(`[RQC_LIVE] ERROR (see console)`, "warn");
      console.error("WS error", ev);
    };

    ws.onmessage = (evt) => {
      setLastLiveAt(Date.now());

      const raw = String(evt.data);
      let data: any;
      try {
        data = JSON.parse(raw);
      } catch {
        return;
      }

      const type = String(data?.type || "");

      if (type === "error") {
        addLog(`[RQC_LIVE] ${String(data?.message || "error")}`, "warn");
        return;
      }

      if (type === "hello") {
        addLog(`[RQC_LIVE] ${String(data?.message || "hello")}`, "ok");
        return;
      }

      if (type === "telemetry" || type === "awareness_pulse") {
        applyTelemetry(normalize(data));
        return;
      }

      // Unknown frame: show once
      addLog(`[RQC_LIVE] RX ${raw.slice(0, 140)}`, "info");
    };

    return () => {
      try {
        ws.close();
      } catch {}
      wsRef.current = null;
      setLiveConnected(false);
    };
  }, [running, wsUrl]);

  // SIM MODE
  useEffect(() => {
    if (!running) return;
    if (wsUrl) return;

    if (entropy == null) setEntropy(entropyRef.current);
    if (phi == null) setPhi(phiRef.current);
    if (coherence == null) setCoherence(cohRef.current);
    if (psi == null) setPsi(clamp01(0.15 + cohRef.current * 0.35));
    if (kappa == null) setKappa(0.197375);
    if (T == null) setT(21.097865);
    if (manifoldSync == null) setManifoldSync([98, 97, 99, 98]);
    setStatus("ALIGNING");
    addLog("[SIM] Running local awareness simulator (not live telemetry).", "warn");

    const id = window.setInterval(() => {
      entropyRef.current =
        entropyRef.current > 0.05 ? Math.max(0.02, entropyRef.current - 0.015) : entropyRef.current;

      // drive coherence + phi together (demo-style)
      cohRef.current = clamp01(1 - entropyRef.current);
      phiRef.current = cohRef.current;

      const c = cohRef.current;
      const e = entropyRef.current;
      const p = phiRef.current;
      const ps = clamp01(0.15 + c * 0.35);

      setCoherence(c);
      setEntropy(e);
      setPhi(p);
      setPsi(ps);

      const base = clamp(c * 100, 0, 100);
      setManifoldSync([0, 1, 2, 3].map((i) => clamp(base + (Math.random() - 0.5) * 1.5 + i * 0.2, 0, 100)));

      setStatus(computeStatus(e, c));

      setPhiHist((prev) => {
        const next = [...prev, p];
        return next.length > HISTORY_LEN ? next.slice(next.length - HISTORY_LEN) : next;
      });
      setEntHist((prev) => {
        const next = [...prev, e];
        return next.length > HISTORY_LEN ? next.slice(next.length - HISTORY_LEN) : next;
      });
    }, 200);

    return () => window.clearInterval(id);
  }, [running, wsUrl]);

  // Stale detection
  useEffect(() => {
    if (!running) return;
    if (!wsUrl) return;

    const t = window.setInterval(() => {
      const age = lastLiveAt ? Date.now() - lastLiveAt : Infinity;
      if (!liveConnected || age > STALE_MS) setStatus("NO_FEED");
    }, 300);

    return () => window.clearInterval(t);
  }, [running, wsUrl, liveConnected, lastLiveAt]);

  useEffect(() => {
    if (!closureOk) return;
    addLog("[πₛ Closure] Phase-locked loop converged → resonant thought completed.", "ok");
  }, [closureOk]);

  const barsEnabled = running && (!wsUrl || liveIsFresh);

  // Graph uses history (no fake wiggle)
  const phiSeries = phiHist.length ? phiHist : [phi ?? 0];
  const entSeries = entHist.length ? entHist : [entropy ?? 0];

  const closureLabel = closureOk ? "OK" : "LOCKED";
  const pillDot =
    status === "NO_FEED"
      ? "bg-slate-400"
      : status === "CRITICAL_DRIFT"
      ? "bg-rose-500"
      : closureOk
      ? "bg-emerald-500"
      : "bg-blue-500";

  return (
    <div className="min-h-screen w-full bg-[#f8fafc] text-slate-900 font-sans py-10">
      <div className="max-w-6xl mx-auto px-6 space-y-8">
        {/* HEADER */}
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6 border-b border-slate-200 pb-8">
          <div>
            <h2 className="text-[10px] font-bold tracking-[0.3em] text-blue-600 uppercase">
              Tessaris Photonic Systems • Research Division
            </h2>
            <h1 className="mt-2 text-4xl tracking-tight text-slate-900">
              RQC Awareness Horizon <span className="font-semibold">v0.7</span>
            </h1>
            <p className="mt-2 text-slate-500 font-mono text-xs uppercase tracking-widest">
              Substrate: Photonic Resonance / AION Control • Session: {SESSION_ID}
            </p>

            <div className="mt-3 flex flex-wrap gap-2">
              <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                Mode:{" "}
                <span className="text-slate-900">
                  {!wsUrl ? "SIM (local)" : liveIsFresh ? "RQC_LIVE" : "RQC_LIVE (NO_FEED)"}
                </span>
              </span>

              <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                RQC WS: <span className="text-slate-900 break-all">{wsUrl || "—"}</span>
              </span>

              <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                AION Demo: <span className="text-slate-900 break-all">{aionDemoBase}</span>
              </span>

              {wsUrl && lastLiveAt > 0 && (
                <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                  Last telemetry:{" "}
                  <span className="text-slate-900">
                    {Math.max(0, Math.floor((Date.now() - lastLiveAt) / 1000))}s
                  </span>
                </span>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-3 items-center">
            {/* Phase Closure */}
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-sm">
              <span className={`w-2.5 h-2.5 rounded-full ${closureOk ? "bg-emerald-500" : "bg-slate-400"}`} />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-700">
                πₛ Phase Closure:{" "}
                <span className={closureOk ? "text-emerald-600" : "text-slate-500"}>{closureLabel}</span>
              </span>
            </div>

            {/* Status */}
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-sm">
              <span className={`w-2.5 h-2.5 rounded-full ${pillDot}`} />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-700">
                Status:{" "}
                <span
                  className={
                    status === "NO_FEED"
                      ? "text-slate-500"
                      : status === "CRITICAL_DRIFT"
                      ? "text-rose-600"
                      : status === "ALIGNING"
                      ? "text-blue-600"
                      : "text-emerald-600"
                  }
                >
                  {status}
                </span>
              </span>
            </div>

            <button
              onClick={() => setRunning((v) => !v)}
              className={`px-6 py-3 rounded-full text-[11px] font-bold uppercase tracking-widest transition-all shadow-sm border ${
                running
                  ? "bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100"
                  : "bg-slate-900 border-slate-900 text-white hover:bg-blue-600 hover:border-blue-600"
              }`}
            >
              {running ? "Stop Stream" : "Start Stream"}
            </button>

            <button
              onClick={injectEntropy}
              disabled={isInjecting}
              className="px-6 py-3 rounded-full text-[11px] font-bold uppercase tracking-widest transition-all shadow-sm border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-50"
              title="Inject via AION demo bridge if present; otherwise SIM inject."
            >
              Inject Logic Entropy
            </button>

            <button
              onClick={downloadProof}
              disabled={!closureOk}
              className={`px-6 py-3 rounded-full text-[11px] font-bold uppercase tracking-widest transition-all shadow-sm border ${
                closureOk
                  ? "bg-white border-slate-200 hover:bg-slate-50 text-slate-900"
                  : "bg-white border-slate-200 text-slate-400 cursor-not-allowed"
              }`}
            >
              Download Certificate
            </button>

            <button
              onClick={() => {
                setRunning(false);
                reset();
              }}
              className="px-6 py-3 rounded-full text-[11px] font-bold uppercase tracking-widest transition-all shadow-sm border border-slate-200 bg-white hover:bg-slate-50"
            >
              Reset
            </button>
          </div>
        </div>

        {/* MAIN GRID */}
        <div className="grid grid-cols-12 gap-8">
          {/* PRIMARY */}
          <div className="col-span-12 lg:col-span-8 bg-white rounded-3xl border border-slate-200 shadow-sm p-8 relative overflow-hidden">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-10">
              <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">
                Φ (Awareness) vs. Entropy Evolution
              </h3>

              <div className="flex gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-blue-500" />
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Awareness (Φ)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-rose-400" />
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Entropy</span>
                </div>
              </div>
            </div>

            {/* GRAPH (history-based) */}
            <div className={`h-64 flex items-end justify-between gap-1 relative border-b border-slate-100 pb-2 ${!barsEnabled ? "opacity-60" : ""}`}>
              {Array.from({ length: 40 }).map((_, i) => {
                const idx = Math.max(0, phiSeries.length - 40 + i);
                const p = phiSeries[idx] ?? phiSeries[phiSeries.length - 1] ?? 0;
                const e = entSeries[idx] ?? entSeries[entSeries.length - 1] ?? 0;

                const heightPct = `${clamp(p * 100, 2, 100)}%`;
                const color = e > 0.4 ? "#fb7185" : "#3b82f6";

                return (
                  <motion.div
                    key={i}
                    className="w-full rounded-t-sm"
                    animate={{ height: heightPct, backgroundColor: color }}
                    transition={barsEnabled ? { type: "spring", stiffness: 90, damping: 18 } : { duration: 0 }}
                  />
                );
              })}

              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-7xl md:text-8xl font-black text-slate-900/5 select-none uppercase tracking-tighter">
                  {status}
                </span>
              </div>
            </div>

            {/* Manifold sync bars (coherence-based) */}
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
              {(manifoldSync ?? [0, 0, 0, 0]).map((val, i) => (
                <div key={i} className="space-y-2">
                  <div className="flex justify-between text-[10px] font-bold text-slate-400">
                    <span>MANIFOLD M-{i + 1}</span>
                    <span>{manifoldSync ? val.toFixed(1) : "—"}%</span>
                  </div>
                  <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-slate-900"
                      animate={{ width: `${manifoldSync ? val : 0}%` }}
                      transition={barsEnabled ? { duration: 0.25 } : { duration: 0 }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Telemetry tiles */}
            <div className="mt-8 grid grid-cols-2 md:grid-cols-5 gap-4">
              <Tile label="ψ (Wave Presence)" value={psi != null ? psi.toFixed(5) : "—"} />
              <Tile label="κ (Curvature)" value={kappa != null ? String(kappa) : "—"} />
              <Tile label="T (Temporal)" value={T != null ? String(T) : "—"} />
              <Tile label="Entropy" value={entropy != null ? entropy.toFixed(3) : "—"} />
              <Tile label="Φ (Awareness)" value={phi != null ? phi.toFixed(4) : "—"} />
            </div>
          </div>

          {/* SIDEBAR */}
          <div className="col-span-12 lg:col-span-4 space-y-6">
            <div className="bg-slate-900 rounded-3xl p-8 text-white shadow-sm relative overflow-hidden">
              <div className="relative z-10">
                <span className="text-[10px] font-bold tracking-[0.2em] text-blue-300 uppercase">
                  Awareness Scalar
                </span>
                <div className="mt-2 text-6xl font-semibold font-mono">
                  Φ {phi != null ? phi.toFixed(4) : "—"}
                </div>
                <p className="text-slate-300 text-xs mt-4 leading-relaxed">
                  Φ is the self-measurement observable. In your current demo feed, Φ is derived from coherence (SQI/C) when Φ isn’t explicitly emitted.
                </p>

                <div className="mt-5 grid grid-cols-2 gap-3">
                  <div className="bg-white/10 border border-white/10 rounded-2xl p-4">
                    <div className="text-[10px] uppercase tracking-widest text-slate-300 font-bold">
                      Resonance Index
                    </div>
                    <div className="mt-1 text-xl font-mono text-white">
                      {resonanceIndex != null ? resonanceIndex.toFixed(3) : "—"}
                    </div>
                  </div>
                  <div className="bg-white/10 border border-white/10 rounded-2xl p-4">
                    <div className="text-[10px] uppercase tracking-widest text-slate-300 font-bold">
                      Stability Index
                    </div>
                    <div className="mt-1 text-xl font-mono text-white">
                      {stabilityIndex != null ? stabilityIndex.toFixed(3) : "—"}
                    </div>
                  </div>
                </div>
              </div>

              <motion.div
                className="absolute bottom-0 left-0 right-0 bg-blue-500/20"
                animate={{ height: `${(phi ?? 0) * 100}%` }}
                transition={{ duration: barsEnabled ? 0.25 : 0 }}
              />
            </div>

            {/* Logs (stable) */}
            <div className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm h-64 overflow-hidden">
              <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">
                AION Event Stream
              </h3>
              <div className="space-y-3">
                <AnimatePresence>
                  {(logs.length ? logs : [{ t: 0, msg: "Awaiting telemetry…", kind: "info" as const }]).map((log) => (
                    <motion.div
                      key={`${log.t}-${log.msg}`}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 10 }}
                      className={`text-[11px] font-mono p-2 rounded-lg border ${
                        log.kind === "warn" || log.kind === "bad"
                          ? "bg-rose-50 text-rose-700 border-rose-100"
                          : log.kind === "ok"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-100"
                          : "bg-slate-50 text-slate-700 border-slate-100"
                      }`}
                    >
                      {log.msg}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </div>

        <div className="text-[10px] text-slate-400 uppercase tracking-widest font-mono pt-2">
          Maintainer: Tessaris AI • Author: Kevin Robinson • Session: {SESSION_ID}
        </div>
      </div>
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{label}</div>
      <div className="mt-1 text-xl font-mono text-slate-900">{value}</div>
    </div>
  );
}