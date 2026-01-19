// frontend/tabs/Aion/AionCognitiveDashboard.tsx
"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";

type AnyObj = Record<string, any>;
type FeedItem = { ts: number; kind: string; payload: AnyObj; raw?: string };

function clamp01(x: number) {
  if (!Number.isFinite(x)) return 0;
  return Math.max(0, Math.min(1, x));
}

function fmt3(x: any) {
  const n = typeof x === "number" ? x : Number(x);
  return Number.isFinite(n) ? n.toFixed(3) : "—";
}

function fmtAge(ms?: number | null) {
  if (ms == null || !Number.isFinite(ms)) return "—";
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${s % 60}s`;
}

function toneFor(v: number, goodMin = 0.975, warnMin = 0.85) {
  if (v >= goodMin) return "bg-emerald-500";
  if (v >= warnMin) return "bg-amber-500";
  return "bg-rose-500";
}

function pickWsUrl() {
  const envWs = process.env.NEXT_PUBLIC_AION_DASHBOARD_WS;
  if (envWs) return envWs;

  if (typeof window !== "undefined") {
    // In Next dev server (3000), default to backend 8080.
    if (window.location.port === "3000") return `ws://127.0.0.1:8080/api/aion/dashboard/ws`;

    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${window.location.host}/api/aion/dashboard/ws`;
  }

  return "ws://127.0.0.1:8080/api/aion/dashboard/ws";
}

function pickApiBase() {
  // optional override (useful when FE served on 3000 and BE on 8080)
  return (
    process.env.NEXT_PUBLIC_AION_API_BASE ||
    (typeof window !== "undefined" ? "" : "")
  );
}

function extractMetrics(obj: AnyObj) {
  // supports:
  //  - {command, SQI, ρ, Ī, ΔΦ, ⟲, ...}
  //  - {command, metrics:{...}}
  //  - {ok, ... , state:{...}} etc
  const m = obj?.metrics && typeof obj.metrics === "object" ? obj.metrics : obj;

  const SQI = m.SQI ?? m.sqi ?? m.sqi_checkpoint;
  const rho = m["ρ"] ?? m.rho ?? m["Φ_coherence"] ?? m["Phi_coherence"];
  const iota = m["Ī"] ?? m.iota ?? m["I"] ?? m["Φ_entropy"] ?? m["Phi_entropy"];
  const dphi = m["ΔΦ"] ?? m.dphi ?? m.delta_phi ?? m.resonance_delta;
  const eq = m["⟲"] ?? m.res_eq ?? m.equilibrium;

  const locked = m.locked ?? obj.locked;
  const threshold = m.threshold ?? obj.threshold;
  const lock_id = m.lock_id ?? obj.lock_id;

  return { SQI, rho, iota, dphi, eq, locked, threshold, lock_id };
}

function findLatestMetricItem(items: FeedItem[]) {
  // Skip the WS hello and anything without metrics-ish fields.
  for (const it of items) {
    const p = it.payload || {};
    const kind = String(p.command || p.type || it.kind || "").toLowerCase();
    if (kind === "hello") continue;

    const mm = extractMetrics(p);
    const has =
      mm.SQI != null ||
      mm.rho != null ||
      mm.iota != null ||
      mm.dphi != null ||
      mm.eq != null ||
      mm.locked != null ||
      mm.threshold != null ||
      mm.lock_id != null;

    if (has) return it;
  }
  return null;
}

async function safeJson(r: Response) {
  try {
    return await r.json();
  } catch {
    return {};
  }
}

export default function AionCognitiveDashboard() {
  const wsUrl = useMemo(() => pickWsUrl(), []);
  const apiBase = useMemo(() => pickApiBase(), []);

  const [status, setStatus] = useState<"connecting" | "open" | "closed" | "error">("connecting");
  const [lastMsgAt, setLastMsgAt] = useState<number | null>(null);
  const [items, setItems] = useState<FeedItem[]>([]);
  const [paused, setPaused] = useState(false);

  // Controls
  const [teachTerm, setTeachTerm] = useState("homeostasis");
  const [teachLevel, setTeachLevel] = useState(1);
  const [askQ, setAskQ] = useState("what is homeostasis?");
  const [checkpointTerm, setCheckpointTerm] = useState("homeostasis");
  const [lockTerm, setLockTerm] = useState("homeostasis");
  const [lockThr, setLockThr] = useState(0.975);
  const [lockWindowSec, setLockWindowSec] = useState(300);

  const [busy, setBusy] = useState<null | "teach" | "ask" | "checkpoint" | "lock">(null);
  const [lastActionErr, setLastActionErr] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(250);

  const metricItem = useMemo(() => findLatestMetricItem(items), [items]);

  const latest = useMemo(() => {
    const base = metricItem?.payload || {};
    const kind = base.command || base.type || metricItem?.kind || "—";
    const term = base.term || base.topic || base.label || base.lambda || "—";
    const mm = extractMetrics(base);
    return {
      kind,
      term,
      ...mm,
    };
  }, [metricItem]);

  useEffect(() => {
    let alive = true;

    function connect() {
      if (!alive) return;
      setStatus("connecting");

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!alive) return;
        setStatus("open");
        backoffRef.current = 250;
      };

      ws.onclose = () => {
        if (!alive) return;
        setStatus("closed");
        const wait = Math.min(4000, backoffRef.current);
        backoffRef.current = Math.min(4000, backoffRef.current * 1.6);
        setTimeout(connect, wait);
      };

      ws.onerror = () => {
        if (!alive) return;
        setStatus("error");
        try {
          ws.close();
        } catch {}
      };

      ws.onmessage = (ev) => {
        if (!alive) return;
        setLastMsgAt(Date.now());
        if (paused) return;

        const raw = typeof ev.data === "string" ? ev.data : "";
        let obj: AnyObj = {};
        try {
          obj = raw ? JSON.parse(raw) : {};
        } catch {
          obj = { _raw: raw };
        }

        const kind = obj.command || obj.type || "message";
        const ts =
          typeof obj.ts === "number"
            ? obj.ts
            : typeof obj.timestamp === "number"
            ? obj.timestamp
            : Date.now() / 1000;

        const item: FeedItem = { ts, kind, payload: obj, raw };
        setItems((prev) => [item, ...prev].slice(0, 400));
      };
    }

    connect();
    return () => {
      alive = false;
      try {
        wsRef.current?.close();
      } catch {}
      wsRef.current = null;
    };
  }, [wsUrl, paused]);

  const ageMs = lastMsgAt ? Date.now() - lastMsgAt : null;

  const eqNum = Number(latest.eq);
  const eq = Number.isFinite(eqNum) ? clamp01(eqNum) : 0;
  const eqTone = toneFor(eq);

  async function doTeach() {
    setBusy("teach");
    setLastActionErr(null);
    try {
      const r = await fetch(`${apiBase}/api/aion/teach`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ term: teachTerm, level: teachLevel }),
      });
      const j = await safeJson(r);
      if (!r.ok) throw new Error(j?.detail || `teach failed (${r.status})`);
    } catch (e: any) {
      setLastActionErr(String(e?.message || e));
    } finally {
      setBusy(null);
    }
  }

  async function doAsk() {
    setBusy("ask");
    setLastActionErr(null);
    try {
      const r = await fetch(`${apiBase}/api/aion/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: askQ }),
      });
      const j = await safeJson(r);
      if (!r.ok) throw new Error(j?.detail || `ask failed (${r.status})`);
    } catch (e: any) {
      setLastActionErr(String(e?.message || e));
    } finally {
      setBusy(null);
    }
  }

  async function doCheckpoint() {
    setBusy("checkpoint");
    setLastActionErr(null);
    try {
      const r = await fetch(`${apiBase}/api/aion/checkpoint`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ term: checkpointTerm }),
      });
      const j = await safeJson(r);
      if (!r.ok) throw new Error(j?.detail || `checkpoint failed (${r.status})`);
    } catch (e: any) {
      setLastActionErr(String(e?.message || e));
    } finally {
      setBusy(null);
    }
  }

  async function doHomeostasisLock() {
    setBusy("lock");
    setLastActionErr(null);
    try {
      const r = await fetch(`${apiBase}/api/aion/homeostasis_lock`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          term: lockTerm,
          threshold: lockThr,
          window_s: lockWindowSec,
        }),
      });
      const j = await safeJson(r);
      if (!r.ok) throw new Error(j?.detail || `homeostasis_lock failed (${r.status})`);
    } catch (e: any) {
      setLastActionErr(String(e?.message || e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="rounded-3xl border border-black/10 bg-white p-8 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="text-2xl font-black tracking-tight">AION Cognitive Dashboard</div>
          <div className="mt-1 font-mono text-xs text-gray-500">
            WS feed: <span className="text-gray-700">{wsUrl}</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="rounded-full border border-black/10 bg-black/5 px-3 py-1 font-mono text-[11px]">
            WS: <span className="font-bold">{status}</span> · last:{" "}
            <span className="font-bold">{fmtAge(ageMs)}</span>
          </div>
          <button
            className="rounded-xl border border-black/10 bg-white px-4 py-2 text-xs font-bold hover:bg-black/5"
            onClick={() => setPaused((p) => !p)}
          >
            {paused ? "Resume" : "Pause"}
          </button>
          <button
            className="rounded-xl border border-black/10 bg-white px-4 py-2 text-xs font-bold hover:bg-black/5"
            onClick={() => setItems([])}
          >
            Clear
          </button>
        </div>
      </div>

      {/* Controls */}
      <div className="mt-6 grid grid-cols-1 gap-4 rounded-2xl border border-black/10 bg-white p-6 lg:grid-cols-2">
        <div>
          <div className="text-xs font-black tracking-widest text-gray-500 uppercase">Teach</div>
          <div className="mt-3 flex gap-2">
            <input
              value={teachTerm}
              onChange={(e) => setTeachTerm(e.target.value)}
              className="w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm font-mono"
              placeholder="term (e.g. homeostasis)"
            />
            <input
              value={teachLevel}
              onChange={(e) => setTeachLevel(Number(e.target.value || 1))}
              type="number"
              min={1}
              max={9}
              className="w-24 rounded-xl border border-black/10 bg-white px-3 py-2 text-sm font-mono"
            />
            <button
              onClick={doTeach}
              disabled={busy !== null}
              className="rounded-xl border border-black/10 bg-black px-4 py-2 text-sm font-bold text-white hover:bg-gray-800 disabled:opacity-50"
            >
              {busy === "teach" ? "Teaching…" : "Teach"}
            </button>
          </div>
        </div>

        <div>
          <div className="text-xs font-black tracking-widest text-gray-500 uppercase">Ask</div>
          <div className="mt-3 flex gap-2">
            <input
              value={askQ}
              onChange={(e) => setAskQ(e.target.value)}
              className="w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm font-mono"
              placeholder='question (e.g. "what is homeostasis?")'
            />
            <button
              onClick={doAsk}
              disabled={busy !== null}
              className="rounded-xl border border-black/10 bg-white px-4 py-2 text-sm font-bold hover:bg-black/5 disabled:opacity-50"
            >
              {busy === "ask" ? "Asking…" : "Ask"}
            </button>
          </div>
        </div>

        <div>
          <div className="text-xs font-black tracking-widest text-gray-500 uppercase">Checkpoint</div>
          <div className="mt-3 flex gap-2">
            <input
              value={checkpointTerm}
              onChange={(e) => setCheckpointTerm(e.target.value)}
              className="w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm font-mono"
              placeholder="term (default homeostasis)"
            />
            <button
              onClick={doCheckpoint}
              disabled={busy !== null}
              className="rounded-xl border border-black/10 bg-white px-4 py-2 text-sm font-bold hover:bg-black/5 disabled:opacity-50"
            >
              {busy === "checkpoint" ? "Checkpoint…" : "Checkpoint"}
            </button>
          </div>
          <div className="mt-2 font-mono text-[11px] text-gray-500">
            Writes a <span className="font-bold">sqi_checkpoint</span> event (required before lock).
          </div>
        </div>

        <div>
          <div className="text-xs font-black tracking-widest text-gray-500 uppercase">Homeostasis Lock</div>
          <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-3">
            <input
              value={lockTerm}
              onChange={(e) => setLockTerm(e.target.value)}
              className="w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm font-mono md:col-span-2"
              placeholder="term (homeostasis)"
            />
            <div className="flex gap-2">
              <input
                value={lockThr}
                onChange={(e) => setLockThr(Number(e.target.value || 0.975))}
                type="number"
                step="0.001"
                min={0}
                max={1}
                className="w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm font-mono"
                title="threshold"
              />
              <input
                value={lockWindowSec}
                onChange={(e) => setLockWindowSec(Number(e.target.value || 300))}
                type="number"
                min={1}
                className="w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm font-mono"
                title="window (sec)"
              />
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <button
              onClick={doHomeostasisLock}
              disabled={busy !== null}
              className="rounded-xl border border-black/10 bg-black px-4 py-2 text-sm font-bold text-white hover:bg-gray-800 disabled:opacity-50"
            >
              {busy === "lock" ? "Locking…" : "Attempt Lock"}
            </button>
            <div className="font-mono text-[11px] text-gray-500">
              Calls <span className="font-bold">POST /api/aion/homeostasis_lock</span>
            </div>
          </div>
        </div>
                <div>
          <div className="text-xs font-black tracking-widest text-gray-500 uppercase">Checkpoint</div>
          <div className="mt-3 flex gap-2">
            <input
              value={checkpointTerm}
              onChange={(e) => setCheckpointTerm(e.target.value)}
              className="w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm font-mono"
              placeholder="term (default homeostasis)"
            />
            <button
              onClick={doCheckpoint}
              disabled={busy !== null}
              className="rounded-xl border border-black/10 bg-white px-4 py-2 text-sm font-bold hover:bg-black/5 disabled:opacity-50"
            >
              {busy === "checkpoint" ? "Checkpoint…" : "Checkpoint"}
            </button>
          </div>
          <div className="mt-2 font-mono text-[11px] text-gray-500">
            Writes a <span className="font-bold">sqi_checkpoint</span> event (required before lock).
          </div>
        </div>

        <div>
          <div className="text-xs font-black tracking-widest text-gray-500 uppercase">Homeostasis Lock</div>

          <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-3">
            <input
              value={lockTerm}
              onChange={(e) => setLockTerm(e.target.value)}
              className="w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm font-mono md:col-span-2"
              placeholder="term (homeostasis)"
            />

            <div className="flex gap-2">
              <input
                value={lockThr}
                onChange={(e) => setLockThr(Number(e.target.value || 0.975))}
                type="number"
                step="0.001"
                min={0}
                max={1}
                className="w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm font-mono"
                title="threshold"
              />
              <input
                value={lockWindowSec}
                onChange={(e) => setLockWindowSec(Number(e.target.value || 300))}
                type="number"
                min={1}
                className="w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm font-mono"
                title="window (sec)"
              />
            </div>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <button
              onClick={doHomeostasisLock}
              disabled={busy !== null}
              className="rounded-xl border border-black/10 bg-black px-4 py-2 text-sm font-bold text-white hover:bg-gray-800 disabled:opacity-50"
            >
              {busy === "lock" ? "Locking…" : "Attempt Lock"}
            </button>

            <div className="font-mono text-[11px] text-gray-500">
              Calls <span className="font-bold">POST /api/aion/homeostasis_lock</span>
            </div>
          </div>
        </div>

        {lastActionErr ? (
          <div className="lg:col-span-2 rounded-xl border border-rose-200 bg-rose-50 p-3 font-mono text-xs text-rose-700">
            {lastActionErr}
          </div>
        ) : null}

        <div className="lg:col-span-2 font-mono text-[11px] text-gray-500">
          Tip: If FE is on <span className="font-bold">:3000</span> and BE is on{" "}
          <span className="font-bold">:8080</span>, set{" "}
          <span className="font-bold">NEXT_PUBLIC_AION_API_BASE=http://127.0.0.1:8080</span>.
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-black/10 bg-white p-6">
          <div className="text-xs font-black tracking-widest text-gray-500 uppercase">Latest Metrics</div>

          <div className="mt-4 space-y-3 font-mono text-sm">
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">event</span>
              <span className="font-bold">{String(latest.kind)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">term</span>
              <span className="font-bold">{String(latest.term)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">SQI</span>
              <span className="font-bold">{fmt3(latest.SQI)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">ρ</span>
              <span className="font-bold">{fmt3(latest.rho)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">Ī</span>
              <span className="font-bold">{fmt3(latest.iota)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">ΔΦ</span>
              <span className="font-bold">{fmt3(latest.dphi)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">⟲</span>
              <span className="font-bold">{fmt3(latest.eq)}</span>
            </div>

            <div className="pt-2">
              <div className="mb-2 text-[11px] font-black tracking-widest text-gray-500 uppercase">
                Homeostasis ⟲
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-black/10">
                <div
                  className={`${eqTone} h-full transition-all duration-500`}
                  style={{ width: `${Math.round(eq * 100)}%` }}
                />
              </div>
              <div className="mt-2 flex justify-between text-[10px] text-gray-400">
                <span>0.00</span>
                <span className="font-bold text-gray-700">{eq.toFixed(3)}</span>
                <span>1.00</span>
              </div>
            </div>

            <div className="pt-2 text-[11px]">
              <div className="flex justify-between">
                <span className="text-gray-500">lock</span>
                <span className="font-bold">
                  {latest.locked === true ? "LOCKED" : latest.locked === false ? "UNLOCKED" : "—"}
                </span>
              </div>
              {latest.threshold != null ? (
                <div className="mt-1 text-gray-500">thr={String(latest.threshold)}</div>
              ) : null}
              {latest.lock_id ? (
                <div className="mt-1 text-gray-500">lock_id={String(latest.lock_id)}</div>
              ) : null}
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 rounded-2xl border border-black/10 bg-white p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-xs font-black tracking-widest text-gray-500 uppercase">Live Feed</div>
              <div className="mt-1 font-mono text-[11px] text-gray-400">
                Use buttons above (or CLI) — events appear here in realtime.
              </div>
            </div>
            <div className="font-mono text-[11px] text-gray-500">{items.length} events</div>
          </div>

          <div className="mt-4 max-h-[560px] overflow-auto rounded-xl border border-black/10 bg-black/[0.03]">
            {items.length === 0 ? (
              <div className="p-4 font-mono text-xs text-gray-500">Waiting for events…</div>
            ) : (
              <ul className="divide-y divide-black/10">
                {items.map((it, idx) => (
                  <li key={`${it.ts}-${idx}`} className="p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-mono text-[11px] text-gray-500">
                        {new Date(it.ts * 1000).toLocaleString()}
                      </div>
                      <div className="rounded-full border border-black/10 bg-white px-2 py-0.5 font-mono text-[10px] font-bold">
                        {String(it.kind)}
                      </div>
                    </div>
                    <pre className="mt-3 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-white p-3 text-[11px] text-gray-700">
                      {JSON.stringify(it.payload, null, 2)}
                    </pre>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}