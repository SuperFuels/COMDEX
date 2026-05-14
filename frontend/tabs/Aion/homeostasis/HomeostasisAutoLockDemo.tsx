// /workspaces/COMDEX/frontend/tabs/homeostasis/HomeostasisDemo.tsx
"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Series = { avg: number | null; min: number | null; max: number | null; n: number };
type Summary = {
  generated_at?: number;
  events?: number;
  bad_lines?: number;
  paths?: { log?: string; out?: string };
  all?: Record<string, Series>;
  recent?: (Record<string, Series> & { window?: number }) | any;
  breakdown?: {
    mode?: Record<string, number>;
    type?: Record<string, number>;
    base_url?: Record<string, number>;
    command?: Record<string, number>;
    locks?: Record<string, number>;
  };
  homeostasis?: {
    sqi_checkpoint_events?: number;
    homeostasis_lock_events?: number;
    locked_true?: number;
    locked_false?: number;
    locked_rate?: number | null;
    last?: any;
  };
  last?: any;
};

function fmt3(x: any) {
  const n = typeof x === "number" ? x : x != null ? Number(x) : NaN;
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(3);
}
function fmtTS(ts: any) {
  if (ts == null) return "—";
  if (typeof ts === "number") {
    const d = new Date(ts * 1000);
    return isNaN(d.getTime()) ? String(ts) : d.toLocaleString();
  }
  return String(ts);
}

const RULE = "⟲ ≥ threshold + sqi_checkpoint";
const API_SUMMARY = "/api/aion/dashboard";
const API_EVENTS = "/api/aion/dashboard/events";

export default function HomeostasisDemo() {
  const [data, setData] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);

  const [isRunning, setIsRunning] = useState(false);
  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);
  const [showResults, setShowResults] = useState(false);

  // threshold presets (pure UI; backend is source of truth)
  const [thr, setThr] = useState<0.95 | 0.975 | 0.99>(0.975);

  // “live” mode: poll summary/events
  const [live, setLive] = useState(false);
  const pollRef = useRef<any>(null);

  const pushLog = (line: string) => {
    setTerminalLogs((p) => {
      const next = [...p, line];
      return next.length > 220 ? next.slice(-220) : next;
    });
  };

  const fetchSummary = async (refresh = false) => {
    setLoading(true); // NEW
    try {
      const url = `${API_SUMMARY}${refresh ? "?refresh=1" : ""}`;
      pushLog(`$ curl ${url}`);
      const r = await fetch(url, { cache: "no-store" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = (await r.json()) as Summary;
      setData(j);
      pushLog(`>> summary: events=${j.events ?? "?"} bad_lines=${j.bad_lines ?? 0}`);
    } catch (e: any) {
      pushLog(`!! summary fetch failed: ${String(e?.message ?? e)}`);
      setData(null);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchEvents = async (limit = 8) => {
    try {
      const url = `${API_EVENTS}?limit=${limit}`;
      pushLog(`$ curl ${url}`);
      const r = await fetch(url, { cache: "no-store" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = (await r.json()) as any;
      const evs = Array.isArray(j?.events) ? j.events : [];
      if (evs.length) {
        const tail = evs.slice(-Math.min(6, evs.length));
        tail.forEach((ev: any) => {
          const cmd = ev?.command ?? ev?.cmd ?? "event";
          const eq = ev?.["⟲"];
          const locked = ev?.locked;
          const sqi = ev?.SQI;
          pushLog(
            `>> ${cmd} ts=${fmtTS(ev?.timestamp)} ⟲=${fmt3(eq)} SQI=${fmt3(sqi)} locked=${
              typeof locked === "boolean" ? String(locked) : "—"
            }`
          );
        });
      } else {
        pushLog(">> events: (none)");
      }
    } catch (e: any) {
      pushLog(`!! events fetch failed: ${String(e?.message ?? e)}`);
    }
  };

  useEffect(() => {
    // initial load
    fetchSummary(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // live polling: summary + brief events tail
    if (pollRef.current) clearInterval(pollRef.current);
    if (!live) return;

    pollRef.current = setInterval(() => {
      fetchSummary(false);
      // keep this cheap (small limit)
      fetchEvents(6);
    }, 1500);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live]);

  const last = useMemo(() => (data?.homeostasis?.last ?? data?.last ?? null) as any, [data]);

  const locked = useMemo(() => {
    if (!last) return null;
    return typeof last.locked === "boolean" ? last.locked : null;
  }, [last]);

  const statusLabel = locked === true ? "LOCKED" : locked === false ? "UNLOCKED" : "NO DATA";
  const statusClass =
    locked === true
      ? "bg-black text-white"
      : locked === false
      ? "bg-gray-100 text-gray-500"
      : "bg-gray-100 text-gray-400";

  const runGate = async () => {
    setIsRunning(true);
    setShowResults(false);

    // This is a UI “demo terminal”. The real producer is your CLI bridge.
    // We show the canonical flow + then force-refresh summary from backend API.
    const cmd = `$ AION_SILENT_MODE=1 PYTHONPATH=. python backend/simulations/run_aion_cognitive_bridge.py`;
    const cmd2 = `$ (inside CLI) checkpoint [term]`;
    const cmd3 = `$ (inside CLI) homeostasis ${thr} 300`;

    setTerminalLogs([cmd, ">> Launching AION Cognitive Bridge (Dashboard-Ready)...", cmd2]);

    const steps = [
      "Writing sqi_checkpoint event -> data/analysis/aion_live_dashboard.jsonl",
      "Probing resonant equilibrium ⟲(t)",
      "Deriving drift ΔΦ from consecutive ⟲ values (if missing)",
      `Evaluating lock gate: ⟲ ≥ ${thr}`,
      "Emitting homeostasis_lock event + lock_id (when locked=true)",
      "Aggregator refresh: JSONL -> JSON snapshot",
      "Frontend pulls /api/aion/dashboard",
    ];

    steps.forEach((step, i) => {
      setTimeout(async () => {
        pushLog(">> " + step);

        if (i === steps.length - 1) {
          pushLog(cmd3);
          // force compute + pull fresh summary (no Cloud Run required; works locally)
          await fetchSummary(true);
          await fetchEvents(10);

          setIsRunning(false);
          setShowResults(true);
        }
      }, (i + 1) * 320);
    });
  };

  const m = last ?? {};
  const sqi = m.SQI ?? m["SQI"];
  const eq = m["⟲"];
  const dphi = m["ΔΦ"];
  const rho = m["ρ"];
  const iota = m["Ī"];
  const lockId = m.lock_id ?? m["lock_id"];
  const threshold = m.threshold ?? m["threshold"];

  const checkpointCount = data?.homeostasis?.sqi_checkpoint_events ?? 0;
  const lockCount = data?.homeostasis?.homeostasis_lock_events ?? 0;
  const lockRate = data?.homeostasis?.locked_rate ?? null;

  return (
    <div className="w-full space-y-10">
      {/* 1. THE CONTROL HUB */}
      <div className="flex flex-col md:flex-row justify-between items-center bg-white p-8 rounded-[3rem] border border-gray-100 shadow-xl shadow-gray-200/50">
        <div className="mb-4 md:mb-0">
          <div className="text-[10px] font-bold text-[#0071e3] uppercase tracking-[0.2em] mb-1">
            Homeostasis (REAL)
          </div>
          <h3 className="text-xl font-bold text-black">Resonant Equilibrium Auto-Lock</h3>

          <div className="mt-3 flex items-center gap-3">
            <span className={`px-4 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest ${statusClass}`}>
              {statusLabel}
            </span>
            <span className="text-[10px] font-bold uppercase tracking-widest text-gray-300">
              Rule: <span className="text-gray-500">{RULE}</span>
            </span>
          </div>

          <div className="mt-2 text-[11px] text-gray-400">
            Source: <span className="text-gray-500">{API_SUMMARY}</span>{" "}
            <span className="text-gray-300">·</span>{" "}
            events: <span className="text-gray-500">{API_EVENTS}</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex bg-gray-100 p-1.5 rounded-full backdrop-blur-sm">
            {[0.95, 0.975, 0.99].map((v) => (
              <button
                key={v}
                onClick={() => {
                  setThr(v as any);
                  setShowResults(false);
                  setTerminalLogs([]);
                }}
                className={`px-8 py-2.5 rounded-full text-xs font-bold transition-all ${
                  thr === v ? "bg-black text-white shadow-lg" : "text-gray-400 hover:text-gray-600"
                }`}
              >
                ⟲ ≥ {v}
              </button>
            ))}
          </div>

          <button
            onClick={() => setLive((v) => !v)}
            className={`px-8 py-4 rounded-full font-bold text-xs transition-all border ${
              live ? "bg-black text-white border-black" : "bg-white text-black border-gray-200 hover:border-gray-300"
            }`}
          >
            {live ? "LIVE: ON" : "LIVE: OFF"}
          </button>

          <button
            onClick={() => fetchSummary(true)}
            disabled={loading || isRunning}
            className="bg-white text-black px-8 py-4 rounded-full font-bold text-xs border border-gray-200 hover:border-gray-300 transition-all disabled:opacity-50"
          >
            {loading ? "REFRESH…" : "REFRESH"}
          </button>

          <button
            onClick={runGate}
            disabled={isRunning}
            className="bg-[#0071e3] text-white px-10 py-4 rounded-full font-bold text-xs hover:scale-105 active:scale-95 transition-all shadow-blue-200 shadow-xl disabled:opacity-50"
          >
            {isRunning ? "PROBING..." : "RUN GATE"}
          </button>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* 2. THE TERMINAL */}
        <div className="bg-[#0a0a0b] rounded-[2.5rem] p-8 h-[480px] shadow-2xl relative overflow-hidden border border-white/5">
          <div className="flex gap-2 mb-8">
            <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f56]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#27c93f]" />
          </div>

          <div className="font-mono text-[11px] leading-relaxed space-y-2 overflow-auto h-[400px] pr-2">
            {terminalLogs.length === 0 ? (
              <div className="text-gray-500">
                {loading ? "Loading dashboard summary..." : "Press RUN GATE to simulate (or enable LIVE for polling)."}
              </div>
            ) : (
              terminalLogs.map((log, i) => (
                <div
                  key={i}
                  className={
                    log.startsWith("$") ? "text-blue-400" : log.startsWith("!!") ? "text-red-400" : "text-gray-400"
                  }
                >
                  {log}
                </div>
              ))
            )}

            {showResults && (
              <div className="pt-6 mt-6 border-t border-white/10 space-y-1 animate-in slide-in-from-bottom-2 duration-500">
                <div className="text-[#27c93f] font-bold">=== ✅ Homeostasis Gate Snapshot ===</div>

                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Status:</span>
                  <span className="text-white font-bold">{statusLabel}</span>
                </div>

                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Threshold:</span>
                  <span className="text-white">{threshold ?? thr}</span>
                </div>

                <div className="flex justify-between py-1">
                  <span className="text-gray-500">⟲ equilibrium:</span>
                  <span className="text-white">{fmt3(eq)}</span>
                </div>

                <div className="flex justify-between py-1 border-b border-white/5 pb-4">
                  <span className="text-gray-500">ΔΦ drift:</span>
                  <span className="text-white">{fmt3(dphi)}</span>
                </div>

                <div className="flex justify-between py-1">
                  <span className="text-gray-500">SQI:</span>
                  <span className="text-white">{fmt3(sqi)}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-gray-500">ρ coherence:</span>
                  <span className="text-white">{fmt3(rho)}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-gray-500">Ī entropy:</span>
                  <span className="text-white">{fmt3(iota)}</span>
                </div>

                <div className="text-[10px] text-gray-600 mt-4">
                  lock_id: <span className="text-gray-400">{lockId ?? "—"}</span>
                </div>
              </div>
            )}
          </div>

          {isRunning && (
            <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>

        {/* 3. THE LIVE IMPACT DATA */}
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-6">
            <MetricBox label="Checkpoints" value={String(checkpointCount)} sub="sqi_checkpoint" show={!loading} />
            <MetricBox
              label="Lock Rate"
              value={lockRate == null ? "—" : `${Math.round(lockRate * 100)}%`}
              sub="homeostasis_lock"
              show={!loading}
              highlight
            />
          </div>

          <div className="bg-gradient-to-br from-[#1d1d1f] to-black p-10 rounded-[3rem] text-white shadow-2xl flex flex-col justify-between flex-1 relative overflow-hidden group">
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-blue-600/10 rounded-full blur-[100px] group-hover:bg-blue-600/20 transition-all duration-1000" />

            <div>
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-blue-400 mb-2">
                Training Gate
              </div>

              <div className="text-5xl md:text-6xl font-bold italic tracking-tighter">{statusLabel}</div>

              <p className="text-xs text-gray-500 mt-4 leading-relaxed max-w-[380px]">
                Homeostasis is the real-time stability gate for AION training. After a required{" "}
                <strong>sqi_checkpoint</strong>, the system probes resonant equilibrium <strong>⟲</strong>. If ΔΦ is not
                logged by the producer, drift can be derived from consecutive ⟲ reads. When{" "}
                <strong>⟲ ≥ {thr}</strong>, AION emits <strong>homeostasis_lock</strong> with{" "}
                <strong>locked=true</strong> and an optional <strong>lock_id</strong>.
              </p>
            </div>

            <div className="pt-8 mt-8 border-t border-white/10 flex justify-between items-center text-[10px] font-bold text-gray-400 uppercase tracking-widest">
              <span>Last Event</span>
              <span className="text-white">{fmtTS(m.timestamp)}</span>
            </div>

            <div className="pt-3 text-[10px] text-gray-500">
              {data?.events != null ? (
                <>
                  events: <span className="text-gray-300">{data.events}</span> · bad_lines:{" "}
                  <span className="text-gray-300">{data.bad_lines ?? 0}</span> · locks:{" "}
                  <span className="text-gray-300">{lockCount}</span>
                </>
              ) : (
                "No dashboard summary yet. Hit REFRESH or RUN GATE (and ensure backend/api/aion_dashboard.py is mounted)."
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricBox({ label, value, sub, show, highlight = false }: any) {
  return (
    <div className="bg-white p-8 rounded-[2.5rem] border border-gray-100 shadow-lg shadow-gray-200/40">
      <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">{label}</div>
      <div
        className={`text-4xl font-bold italic transition-all duration-700 ${
          show ? "opacity-100" : "opacity-0"
        } ${highlight ? "text-[#0071e3]" : "text-black"}`}
      >
        {value}
      </div>
      <div className="text-[10px] font-bold text-gray-300 uppercase mt-1">{sub}</div>
    </div>
  );
}