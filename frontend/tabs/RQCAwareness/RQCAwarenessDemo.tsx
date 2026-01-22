"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * RQC AWARENESS HORIZON — v0.6 (aligned to backend variability)
 *
 * ✅ RQC LIVE WS:     /resonance
 * ✅ AION Demo Bridge (optional, for inject button + future linkage):
 *      /aion-demo/api/demo/inject_entropy
 *      /aion-demo/api/demo/phi/inject_entropy
 *      /aion-demo/api/demo/phi/recover
 *
 * WS payloads can vary (flat or nested), e.g.:
 *  - { type:"telemetry", metrics:{ ψ, κ, T, Φ, coherence, ... }, source? }
 *  - { type:"telemetry", state:{ metrics:{ ... } } }
 *  - { type:"awareness_pulse", Φ, coherence, message? }
 *  - { type:"hello" | "error", ... }
 */

const SESSION_ID = "a99acc96-acde-48d5-9b6d-d2f434536d5b";

// Stale detection: if LIVE connected but no telemetry within this window → treat as NO_FEED
const STALE_MS = 2_500;

type Mode = "SIM" | "LIVE" | "LIVE_STALE";
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

function pickMetric(m: any, keys: string[]) {
  for (const k of keys) {
    if (m && Object.prototype.hasOwnProperty.call(m, k)) {
      const v = num(m[k]);
      if (v != null) return v;
    }
  }
  return null;
}

/**
 * Normalizes whatever the backend is sending into the UI slots.
 * If a slot can't be derived, it stays null (render "—").
 */
function normalizeRqcMetrics(msg: any) {
  const m = msg?.metrics ?? msg?.state?.metrics ?? msg ?? {};

  // What the UI expects:
  const psi = pickMetric(m, ["ψ", "psi", "presence", "ρ", "rho"]);
  const kappa = pickMetric(m, ["κ", "kappa", "curvature"]);
  const T = pickMetric(m, ["T", "temp", "temporal", "time"]);
  const Phi = pickMetric(m, ["Φ", "phi", "awareness"]);
  const C = pickMetric(m, ["C", "coherence", "SQI", "sqi"]);

  // Also keep some raw variants you may be receiving
  const rho = pickMetric(m, ["ρ", "rho"]);
  const Ibar = pickMetric(m, ["Ī", "Ibar", "Ī", "I"]);

  return { psi, kappa, T, Phi, C, rho, Ibar };
}

/**
 * If you set NEXT_PUBLIC_API_BASE to:
 *   https://...run.app/api
 * we derive origin as:
 *   https://...run.app
 */
function resolveOrigin(): string {
  const apiBase = (
    process.env.NEXT_PUBLIC_AION_API_BASE ||
    process.env.NEXT_PUBLIC_API_BASE ||
    ""
  ).trim();

  const u = apiBase ? safeUrl(apiBase) : null;

  if (u) {
    const p = (u.pathname || "/").replace(/\/+$/, "");
    if (p.endsWith("/api")) u.pathname = p.slice(0, -4) || "/";
    else u.pathname = p || "/";
    u.search = "";
    u.hash = "";
    return u.toString().replace(/\/+$/, "");
  }

  if (typeof window !== "undefined") return window.location.origin;
  return "";
}

function pickRqcWsUrl() {
  const env = (process.env.NEXT_PUBLIC_RQC_WS || "").trim();
  if (env) {
    if (env.startsWith("https://")) return "wss://" + env.slice("https://".length);
    if (env.startsWith("http://")) return "ws://" + env.slice("http://".length);
    return env; // ws:// or wss:// (full URL)
  }

  const origin = resolveOrigin();
  if (origin) {
    const proto = origin.startsWith("https://") ? "wss" : "ws";
    const host = origin.replace(/^https?:\/\//, "");
    return `${proto}://${host}/resonance`;
  }

  // IMPORTANT: do NOT force localhost in prod.
  // Returning "" means: no wsUrl => SIM mode.
  if (typeof window !== "undefined") {
    const isLocal =
      window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    if (isLocal) return "ws://127.0.0.1:8080/resonance";
  }

  return "";
}

function pickAionDemoBase() {
  const env = (process.env.NEXT_PUBLIC_AION_DEMO_BASE || "").trim();
  if (env) return env.replace(/\/+$/, "");
  const origin = resolveOrigin();
  return origin ? `${origin}/aion-demo` : "http://127.0.0.1:8080/aion-demo";
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
  // Truth state: start as null so UI can show NO_FEED until SIM or LIVE pushes values
  const [psi, setPsi] = useState<number | null>(null);
  const [kappa, setKappa] = useState<number | null>(null);
  const [T, setT] = useState<number | null>(null);

  const [entropy, setEntropy] = useState<number | null>(null);
  const [phi, setPhi] = useState<number | null>(null);
  const [coherence, setCoherence] = useState<number | null>(null);

  const [status, setStatus] = useState<"STABLE" | "ALIGNING" | "CRITICAL_DRIFT" | "NO_FEED">(
    "NO_FEED"
  );
  const [manifoldSync, setManifoldSync] = useState<number[] | null>(null);

  const [isInjecting, setIsInjecting] = useState(false);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [running, setRunning] = useState(false);

  const wsUrl = useMemo(() => pickRqcWsUrl(), []);
  const aionDemoBase = useMemo(() => pickAionDemoBase(), []);

  const wsRef = useRef<WebSocket | null>(null);

  const [liveConnected, setLiveConnected] = useState(false);
  const [lastLiveAt, setLastLiveAt] = useState<number>(0);

  const [proofJson, setProofJson] = useState<string>("");

  // Refs to avoid stale-closure bugs in SIM loop
  const entropyRef = useRef<number>(0.15);
  const phiRef = useRef<number>(0.64);
  const cohRef = useRef<number>(0.64);

  const addLog = (msg: string, kind: LogItem["kind"] = "info") => {
    setLogs((prev) => [{ t: Date.now(), msg, kind }, ...prev].slice(0, 8));
  };

  const computeStatus = (e: number, c: number) => {
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

  // Derived indices – only compute when we have real numbers
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
      derived: {
        resonanceIndex,
        stabilityIndex,
        status,
        mode,
        wsUrl: wsUrl || null,
        aionDemoBase,
      },
      generatedAt: new Date().toISOString(),
    };
    return JSON.stringify(payload, null, 2);
  };

  const downloadProof = () => {
    const json = buildProofJsonLd();
    setProofJson(json);

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
    setStatus("NO_FEED");
    setIsInjecting(false);
    setProofJson("");
    setLogs([]);
    addLog("[System] Reset: Awareness Horizon re-armed.", "info");

    entropyRef.current = 0.15;
    phiRef.current = 0.64;
    cohRef.current = 0.64;
  };

  const injectEntropy = async () => {
    setIsInjecting(true);

    // IMPORTANT: /resonance WS is a tail-only stream; it does NOT accept "inject_entropy" messages.
    // If demo bridge exists, hit it (best effort). Otherwise do SIM inject.
    try {
      const r = await postJson(`${aionDemoBase}/api/demo/inject_entropy`, { sessionId: SESSION_ID });
      if (r.ok) {
        addLog(`[AION_DEMO] Inject triggered via ${aionDemoBase}/api/demo/inject_entropy`, "warn");
      } else {
        // try the more specific endpoint
        const r2 = await postJson(`${aionDemoBase}/api/demo/phi/inject_entropy`, {
          sessionId: SESSION_ID,
        });
        if (r2.ok) addLog(`[AION_DEMO] Φ entropy injected via demo bridge.`, "warn");
        else throw new Error(`demo bridge not available (HTTP ${r.status})`);
      }
    } catch {
      // SIM injection fallback
      entropyRef.current = 0.85;
      phiRef.current = 0.32;
      cohRef.current = 0.32;

      setEntropy(0.85);
      setPhi(0.32);
      setCoherence(0.32);
      setStatus("CRITICAL_DRIFT");
      addLog("[SIM] External Entropy Injected: Phase drift detected.", "warn");
      addLog("[SIM] Control loop initializing Φ feedback…", "info");
    }

    window.setTimeout(() => setIsInjecting(false), 900);
  };

  // ─────────────────────────────────────────────────────────────
  // LIVE MODE: connect to /resonance when running
  // ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!running) return;
    if (!wsUrl) return; // SIM mode

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setLiveConnected(true);
      addLog(`[RQC_LIVE] OPEN → ${wsUrl}`, "ok");

      try {
        const hello = { type: "hello", client: "RQCAwarenessDemo", sessionId: SESSION_ID };
        ws.send(JSON.stringify(hello));
        addLog(`[RQC_LIVE] SENT hello`, "info");
      } catch (e: any) {
        addLog(`[RQC_LIVE] SEND failed: ${e?.message || String(e)}`, "warn");
      }
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
      let data: any = null;
      try {
        data = JSON.parse(raw);
      } catch {
        // non-json frame: ignore
        return;
      }

      const type = String(data?.type || "");

      // Avoid spamming logs with full telemetry blobs; log non-telemetry frames verbosely.
      if (type !== "telemetry") {
        addLog(`[RQC_LIVE] RX ${raw.slice(0, 140)}`, "info");
      }

      if (type === "hello") {
        addLog(`[RQC_LIVE] ${String(data?.message || "hello")}`, "ok");
        return;
      }

      if (type === "telemetry") {
        const nm = normalizeRqcMetrics(data);

        const nextPsi = nm.psi;
        const nextKappa = nm.kappa;
        const nextT = nm.T;

        const nextPhi = nm.Phi != null ? clamp01(nm.Phi) : null;
        const nextCoh = nm.C != null ? clamp01(nm.C) : null;

        if (nextPsi != null) setPsi(nextPsi);
        if (nextKappa != null) setKappa(nextKappa);
        if (nextT != null) setT(nextT);
        if (nextPhi != null) setPhi(nextPhi);
        if (nextCoh != null) setCoherence(nextCoh);

        // Entropy proxy: from κ if present; otherwise keep previous entropy
        if (nextKappa != null) setEntropy(clamp01(1 - clamp01(nextKappa)));

        // ManifoldSync is not emitted by /resonance; infer from coherence for display
        if (nextCoh != null) {
          const base = clamp(nextCoh * 100, 0, 100);
          setManifoldSync([0, 1, 2, 3].map((i) => clamp(base + i * 0.2, 0, 100)));
        }

        const eProxy = nextKappa != null ? clamp01(1 - clamp01(nextKappa)) : entropy ?? 0.5;
        const cProxy = nextCoh != null ? nextCoh : coherence ?? 0.5;

        const s = computeStatus(eProxy, cProxy);
        setStatus(s);

        const src = typeof data?.source === "string" ? ` src=${data.source}` : "";

        // Main one-liner (what you actually care about)
        addLog(
          `[Telemetry] ψ=${nextPsi ?? "—"} κ=${nextKappa ?? "—"} T=${nextT ?? "—"} Φ=${nextPhi ?? "—"} C=${nextCoh ?? "—"}${src}`,
          s === "CRITICAL_DRIFT" ? "warn" : "info"
        );

        // Optional: quick “feed health” / raw slots you might be receiving
        if (nm.rho != null || nm.Ibar != null) {
          addLog(`[RQC] SQI=${nextCoh ?? "—"} ρ=${nm.rho ?? "—"} Ī=${nm.Ibar ?? "—"}`, "info");
        }

        return;
      }

      if (type === "awareness_pulse") {
        const msg =
          typeof data?.message === "string" ? data.message : "Awareness pulse detected.";
        addLog(`[RQC] ${msg}`, "ok");

        // Support both flat and nested keys here too
        const nm = normalizeRqcMetrics(data);
        if (nm.Phi != null) setPhi(clamp01(nm.Phi));
        if (nm.C != null) setCoherence(clamp01(nm.C));

        // Some backends send Φ/coherence flat on pulse:
        if (typeof data["Φ"] === "number") setPhi(clamp01(data["Φ"]));
        if (typeof data["coherence"] === "number") setCoherence(clamp01(data["coherence"]));
        return;
      }

      if (type === "error") {
        addLog(`[RQC_LIVE] ${String(data?.message || "error")}`, "warn");
        return;
      }
    };

    return () => {
      try {
        ws.close();
      } catch {}
      wsRef.current = null;
      setLiveConnected(false);
    };
  }, [running, wsUrl]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─────────────────────────────────────────────────────────────
  // SIM MODE: drive state only when running && no wsUrl
  // ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!running) return;

    // If wsUrl exists, we are LIVE; do not run SIM loop
    if (wsUrl) return;

    // initialize SIM values once when starting
    if (entropy == null) setEntropy(entropyRef.current);
    if (phi == null) setPhi(phiRef.current);
    if (coherence == null) setCoherence(cohRef.current);
    if (psi == null) setPsi(0.23896);
    if (kappa == null) setKappa(0.197375);
    if (T == null) setT(21.097865);
    if (manifoldSync == null) setManifoldSync([98, 97, 99, 98]);
    setStatus("ALIGNING");
    addLog("[SIM] Running local awareness simulator (not live telemetry).", "warn");

    const id = window.setInterval(() => {
      entropyRef.current =
        entropyRef.current > 0.05
          ? Math.max(0.02, entropyRef.current - 0.015)
          : entropyRef.current;

      phiRef.current =
        entropyRef.current > 0.05
          ? Math.min(0.99, phiRef.current + 0.02)
          : Math.max(0.92, phiRef.current - 0.005);

      const target = clamp01(phiRef.current);
      cohRef.current = clamp01(cohRef.current + (target - cohRef.current) * 0.18);

      setEntropy(entropyRef.current);
      setPhi(phiRef.current);
      setCoherence(cohRef.current);

      const base = clamp(cohRef.current * 100, 0, 100);
      setManifoldSync(
        [0, 1, 2, 3].map((i) =>
          clamp(base + (Math.random() - 0.5) * 2 + i * 0.3, 90, 100)
        )
      );

      setKappa(clamp01(1 - entropyRef.current * 0.85));
      setPsi(clamp01(0.15 + cohRef.current * 0.35));
      setT((v) => (v == null ? 21.0 : v + Math.sin(Date.now() / 1500) * 0.0002));

      setStatus(computeStatus(entropyRef.current, cohRef.current));
    }, 150);

    return () => window.clearInterval(id);
  }, [running, wsUrl]); // eslint-disable-line react-hooks/exhaustive-deps

  // If LIVE goes stale, show NO_FEED / freeze bars
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
  }, [closureOk]); // eslint-disable-line react-hooks/exhaustive-deps

  const barsEnabled = running && (!wsUrl || liveIsFresh);

  const displayPhi = phi ?? 0;
  const displayEntropy = entropy ?? 0;

  const pillDot =
    status === "NO_FEED"
      ? "bg-slate-400"
      : status === "CRITICAL_DRIFT"
      ? "bg-rose-500"
      : closureOk
      ? "bg-emerald-500"
      : "bg-blue-500";

  const closureLabel = closureOk ? "OK" : "LOCKED";

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
              RQC Awareness Horizon <span className="font-semibold">v0.6</span>
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
                RQC WS: <span className="text-slate-900">{wsUrl || "—"}</span>
              </span>

              <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                AION Demo: <span className="text-slate-900">{aionDemoBase}</span>
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
            {/* Phase Closure pill */}
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-sm">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  closureOk ? "bg-emerald-500" : "bg-slate-400"
                }`}
              />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-700">
                πₛ Phase Closure:{" "}
                <span className={closureOk ? "text-emerald-600" : "text-slate-500"}>
                  {closureLabel}
                </span>
              </span>
            </div>

            {/* System status pill */}
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

            {/* Start/Stop */}
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

            {/* Inject */}
            <button
              onClick={injectEntropy}
              disabled={isInjecting}
              className="px-6 py-3 rounded-full text-[11px] font-bold uppercase tracking-widest transition-all shadow-sm border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-50"
              title="Inject via AION demo bridge if present; otherwise SIM inject. (RQC /resonance WS is read-only.)"
            >
              Inject Logic Entropy
            </button>

            {/* Download proof */}
            <button
              onClick={downloadProof}
              disabled={!closureOk}
              className={`px-6 py-3 rounded-full text-[11px] font-bold uppercase tracking-widest transition-all shadow-sm border ${
                closureOk
                  ? "bg-white border-slate-200 hover:bg-slate-50 text-slate-900"
                  : "bg-white border-slate-200 text-slate-400 cursor-not-allowed"
              }`}
              title={closureOk ? "Download Phase Closure Certificate (JSON-LD)" : "Reach πₛ closure first"}
            >
              Download Certificate
            </button>

            {/* Reset */}
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

        {/* MAIN HUD GRID */}
        <div className="grid grid-cols-12 gap-8">
          {/* PRIMARY VISUALIZER */}
          <div className="col-span-12 lg:col-span-8 bg-white rounded-3xl border border-slate-200 shadow-sm p-8 relative overflow-hidden">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-10">
              <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">
                Φ (Awareness) vs. Entropy Evolution
              </h3>

              <div className="flex gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-blue-500" />
                  <span className="text-[10px] font-bold text-slate-500 uppercase">
                    Awareness (Φ)
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-rose-400" />
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Entropy</span>
                </div>
              </div>
            </div>

            {/* GRAPH AREA */}
            <div
              className={`h-64 flex items-end justify-between gap-1 relative border-b border-slate-100 pb-2 ${
                !barsEnabled ? "opacity-60" : ""
              }`}
            >
              {[...Array(40)].map((_, i) => {
                const base = Math.max(10, displayPhi * 80);
                const wiggle = barsEnabled ? Math.sin(i + Date.now() / 1000) * 10 : 0;
                const heightPct = `${base + wiggle}%`;

                const color = displayEntropy > 0.4 ? "#fb7185" : "#3b82f6";

                return (
                  <motion.div
                    key={i}
                    className="w-full rounded-t-sm"
                    animate={{ height: heightPct, backgroundColor: color }}
                    transition={
                      barsEnabled
                        ? { type: "spring", stiffness: 90, damping: 14 }
                        : { duration: 0 }
                    }
                  />
                );
              })}

              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-7xl md:text-8xl font-black text-slate-900/5 select-none uppercase tracking-tighter">
                  {status}
                </span>
              </div>
            </div>

            {/* Manifold sync bars (inferred if LIVE) */}
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
              <Tile label="κ (Curvature)" value={kappa != null ? kappa.toFixed(6) : "—"} />
              <Tile label="T (Temporal)" value={T != null ? T.toFixed(3) : "—"} />
              <Tile label="Entropy" value={entropy != null ? entropy.toFixed(3) : "—"} />
              <Tile label="Φ (Awareness)" value={phi != null ? phi.toFixed(4) : "—"} />
            </div>

            {/* Proof JSON (optional display) */}
            {proofJson ? (
              <div className="mt-8 bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <div className="flex items-center justify-between">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
                    Phase Closure Certificate (preview)
                  </div>
                  <button
                    className="text-[10px] font-bold uppercase tracking-widest text-blue-700 hover:text-blue-900"
                    onClick={() => navigator.clipboard?.writeText(proofJson)}
                  >
                    Copy
                  </button>
                </div>
                <pre className="mt-3 text-[11px] leading-relaxed text-slate-700 overflow-auto max-h-56">
                  {proofJson}
                </pre>
              </div>
            ) : null}
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
                  Φ is the self-measurement observable exposed by the RQC feed (WS: /resonance).
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

            {/* Logs */}
            <div className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm h-64 overflow-hidden">
              <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">
                AION Event Stream
              </h3>
              <div className="space-y-3">
                <AnimatePresence>
                  {(logs.length
                    ? logs
                    : [{ t: 0, msg: "Awaiting telemetry…", kind: "info" as const }]
                  ).map((log) => (
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