// frontend/tabs/Aion/AionCognitiveDashboard.tsx
"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";

type AnyObj = Record<string, any>;
type FeedItem = { ts: number; kind: string; payload: AnyObj; raw?: string };

/* ------------------------ URL resolution (SOURCE OF TRUTH) ------------------------ */
/**
 * Single rule-set (matches useTessarisTelemetry + Proof-of-Life dashboard):
 *
 * HTTP base comes from:
 *   NEXT_PUBLIC_API_ORIGIN
 *   NEXT_PUBLIC_GLYPHNET_HTTP_BASE
 *   NEXT_PUBLIC_API_URL
 *   NEXT_PUBLIC_API_BASE
 *   NEXT_PUBLIC_AION_API_BASE
 *
 * WS prefix comes from:
 *   NEXT_PUBLIC_WS_PREFIX (default: "/api/ws")
 *
 * This dashboard WS endpoint is assumed to be:
 *   ${WS_PREFIX}/qfc
 * which matches your vite proxy:
 *   "/api/ws/qfc": wsProxy(fastApiHttp)
 */

function stripSlash(s: string) {
  return (s || "").trim().replace(/\/+$/, "");
}

function normalizeHttpBase(raw: string) {
  let b = stripSlash(raw);
  if (!b) return "";
  // tolerate pastes like ".../api" or ".../aion-demo"
  b = b.replace(/\/api$/i, "");
  b = b.replace(/\/aion-demo$/i, "");
  return b;
}

function resolveHttpBase(): string {
  const env =
    (process.env.NEXT_PUBLIC_API_ORIGIN as string | undefined) ||
    (process.env.NEXT_PUBLIC_GLYPHNET_HTTP_BASE as string | undefined) ||
    (process.env.NEXT_PUBLIC_API_URL as string | undefined) ||
    (process.env.NEXT_PUBLIC_API_BASE as string | undefined) ||
    (process.env.NEXT_PUBLIC_AION_API_BASE as string | undefined) ||
    "";

  const cleaned = normalizeHttpBase(env);
  if (cleaned) return cleaned;

  // Local dev: FE :3000 -> BE :8080
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    const port = window.location.port;
    const isLocal = host === "localhost" || host === "127.0.0.1";
    if (isLocal && port === "3000") return "http://127.0.0.1:8080";
    // same-origin only if you truly proxy /api + /api/ws in the FE
    return "";
  }

  return "";
}

/** Convert an HTTP base into WS ORIGIN only (no path). */
function wsOriginFromHttpBase(input: string) {
  const s = (input || "").trim();
  if (!s) return "";

  // already ws(s)://
  if (s.startsWith("ws://") || s.startsWith("wss://")) {
    try {
      const u = new URL(s);
      return `${u.protocol}//${u.host}`;
    } catch {
      return stripSlash(s);
    }
  }

  // http(s)://
  if (s.startsWith("http://") || s.startsWith("https://")) {
    try {
      const u = new URL(s);
      const proto = u.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${u.host}`;
    } catch {
      const cleaned = stripSlash(s);
      if (cleaned.startsWith("https://")) return "wss://" + cleaned.slice("https://".length);
      if (cleaned.startsWith("http://")) return "ws://" + cleaned.slice("http://".length);
      return cleaned;
    }
  }

  // bare host
  return "wss://" + stripSlash(s).replace(/^\/+/, "");
}

function wsPrefix() {
  const p = (process.env.NEXT_PUBLIC_WS_PREFIX || "/api/ws").trim();
  return (p.startsWith("/") ? p : "/" + p).replace(/\/+$/, "");
}

function joinUrl(base: string, path: string) {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (!base) return p; // same-origin
  return stripSlash(base) + p;
}

/* ------------------------ small utils ------------------------ */

function clamp01(x: number) {
  if (!Number.isFinite(x)) return 0;
  return Math.max(0, Math.min(1, x));
}

function fmt3(x: any) {
  const n = typeof x === "number" ? x : x != null ? Number(x) : NaN;
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

async function safeJson(r: Response) {
  try {
    return await r.json();
  } catch {
    return {};
  }
}

async function postJson(url: string, body: any, timeoutMs = 20000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body ?? {}),
      signal: ctrl.signal,
    });
    const j = await safeJson(r);
    return { ok: r.ok, status: r.status, json: j };
  } finally {
    clearTimeout(t);
  }
}

/* ------------------------ payload parsing ------------------------ */

function extractMetrics(obj: AnyObj) {
  const m = obj?.metrics && typeof obj.metrics === "object" ? obj.metrics : obj;

  const SQI = m.SQI ?? m.sqi ?? m.sqi_checkpoint ?? m.checkpoint_sqi;
  const rho = m["ρ"] ?? m.rho ?? m.phi_coherence ?? m["Φ_coherence"] ?? m["Phi_coherence"];
  const iota = m["Ī"] ?? m.iota ?? m.Ibar ?? m["I"] ?? m.phi_entropy ?? m["Φ_entropy"] ?? m["Phi_entropy"];
  const dphi = m["ΔΦ"] ?? m.dphi ?? m.delta_phi ?? m.resonance_delta;
  const eq = m["⟲"] ?? m.eq ?? m.res_eq ?? m.equilibrium;

  const locked = m.locked ?? obj.locked ?? obj?.state?.locked;
  const threshold = m.threshold ?? obj.threshold ?? obj?.state?.threshold;
  const lock_id = m.lock_id ?? obj.lock_id ?? obj?.state?.lock_id;

  return { SQI, rho, iota, dphi, eq, locked, threshold, lock_id };
}

function normalizeTsToSeconds(obj: AnyObj): number {
  const cand = obj?.ts ?? obj?.timestamp ?? obj?.time ?? null;
  if (typeof cand === "number" && Number.isFinite(cand)) {
    return cand > 1e12 ? cand / 1000 : cand;
  }
  return Date.now() / 1000;
}

function findLatestMetricItem(items: FeedItem[]) {
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

/* ------------------------ component ------------------------ */

export default function AionCognitiveDashboard() {
  const httpBase = useMemo(() => resolveHttpBase(), []);
  const apiBase = useMemo(() => httpBase, [httpBase]);

  const wsBase = useMemo(() => wsOriginFromHttpBase(httpBase), [httpBase]);
  const prefix = useMemo(() => wsPrefix(), []);
  const wsUrl = useMemo(() => `${wsBase}${prefix}/qfc`, [wsBase, prefix]);

  const [status, setStatus] = useState<"connecting" | "open" | "closed" | "error">("connecting");
  const [lastMsgAt, setLastMsgAt] = useState<number | null>(null);
  const [items, setItems] = useState<FeedItem[]>([]);
  const [paused, setPaused] = useState(false);

  // don’t reconnect WS when paused changes
  const pausedRef = useRef(paused);
  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

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
  const [lastActionOk, setLastActionOk] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(250);

  const metricItem = useMemo(() => findLatestMetricItem(items), [items]);

  const latest = useMemo(() => {
    const base = metricItem?.payload || {};
    const kind = base.command || base.type || metricItem?.kind || "—";
    const term = base.term || base.topic || base.label || base.lambda || base.namespace || "—";
    const mm = extractMetrics(base);
    return { kind, term, ...mm };
  }, [metricItem]);

  useEffect(() => {
    let alive = true;

    function connect() {
      if (!alive) return;

      // if wsUrl can't be built, don't spam reconnect loops
      if (!wsUrl || !wsUrl.startsWith("ws")) {
        setStatus("error");
        return;
      }

      setStatus("connecting");

      let ws: WebSocket;
      try {
        ws = new WebSocket(wsUrl);
      } catch {
        setStatus("error");
        return;
      }

      wsRef.current = ws;

      ws.onopen = () => {
        if (!alive) return;
        setStatus("open");
        backoffRef.current = 250;
        try {
          ws.send(JSON.stringify({ type: "hello", client: "AionCognitiveDashboard" }));
        } catch {}
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
        if (pausedRef.current) return;

        const raw = typeof ev.data === "string" ? ev.data : "";
        let obj: AnyObj = {};
        try {
          obj = raw ? JSON.parse(raw) : {};
        } catch {
          obj = { _raw: raw };
        }

        const kind = obj.command || obj.type || "message";
        const ts = normalizeTsToSeconds(obj);

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
  }, [wsUrl]);

  const ageMs = lastMsgAt ? Date.now() - lastMsgAt : null;

  const eqNum = Number(latest.eq);
  const eq = Number.isFinite(eqNum) ? clamp01(eqNum) : 0;
  const eqTone = toneFor(eq);

  async function runBusy(name: "teach" | "ask" | "checkpoint" | "lock", fn: () => Promise<void>) {
    setBusy(name);
    setLastActionErr(null);
    setLastActionOk(null);
    try {
      await fn();
    } finally {
      setBusy(null);
    }
  }

  async function doTeach() {
    await runBusy("teach", async () => {
      const { ok, status, json } = await postJson(joinUrl(apiBase, "/api/aion/teach"), { term: teachTerm, level: teachLevel }, 25000);
      if (!ok) throw new Error(json?.detail || `teach failed (${status})`);
      setLastActionOk("Teach: OK");
    }).catch((e: any) => setLastActionErr(String(e?.message || e)));
  }

  async function doAsk() {
    await runBusy("ask", async () => {
      const { ok, status, json } = await postJson(joinUrl(apiBase, "/api/aion/ask"), { question: askQ }, 25000);
      if (!ok) throw new Error(json?.detail || `ask failed (${status})`);
      setLastActionOk("Ask: OK");
    }).catch((e: any) => setLastActionErr(String(e?.message || e)));
  }

  async function doCheckpoint() {
    await runBusy("checkpoint", async () => {
      const { ok, status, json } = await postJson(joinUrl(apiBase, "/api/aion/checkpoint"), { term: checkpointTerm }, 25000);
      if (!ok) throw new Error(json?.detail || `checkpoint failed (${status})`);
      setLastActionOk("Checkpoint: OK");
    }).catch((e: any) => setLastActionErr(String(e?.message || e)));
  }

  async function doHomeostasisLock() {
    await runBusy("lock", async () => {
      const { ok, status, json } = await postJson(
        joinUrl(apiBase, "/api/aion/homeostasis_lock"),
        { term: lockTerm, threshold: lockThr, window_s: lockWindowSec },
        25000
      );
      if (!ok) throw new Error(json?.detail || `homeostasis_lock failed (${status})`);
      setLastActionOk("Homeostasis lock: OK");
    }).catch((e: any) => setLastActionErr(String(e?.message || e)));
  }

  const resolvedApi = apiBase ? apiBase : "(same-origin)";
  const resolvedWs = wsUrl;

  return (
    <div className="rounded-3xl border border-black/10 bg-white p-8 shadow-sm">
      {/* Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="text-2xl font-black tracking-tight">AION Cognitive Dashboard</div>
          <div className="mt-2 grid gap-1 font-mono text-[11px] text-gray-500">
            <div>
              API: <span className="text-gray-700">{resolvedApi}</span>
            </div>
            <div>
              WS: <span className="text-gray-700">{resolvedWs}</span>
            </div>
            <div>
              WS_PREFIX: <span className="text-gray-700">{prefix}</span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="rounded-full border border-black/10 bg-black/5 px-3 py-1 font-mono text-[11px]">
            WS: <span className="font-bold">{status}</span> · last: <span className="font-bold">{fmtAge(ageMs)}</span>
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
          <div className="text-xs font-black tracking-widest text-gray-500 uppercase">Resonant Equilibrium Auto-Lock (REAL)</div>

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

        {lastActionOk ? (
          <div className="lg:col-span-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 font-mono text-xs text-emerald-800">
            {lastActionOk}
          </div>
        ) : null}

        <div className="lg:col-span-2 font-mono text-[11px] text-gray-500">
          Env: set <span className="font-bold">NEXT_PUBLIC_API_URL=https://&lt;cloud-run-host&gt;</span> and{" "}
          <span className="font-bold">NEXT_PUBLIC_WS_PREFIX=/api/ws</span>.
        </div>
      </div>

      {/* Metrics + Feed */}
      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Latest Metrics */}
        <div className="rounded-2xl border border-black/10 bg-white p-6">
          <div className="text-xs font-black tracking-widest text-gray-500 uppercase">Latest Metrics</div>

          <div className="mt-4 space-y-3 font-mono text-sm">
            <Row k="event" v={String(latest.kind)} />
            <Row k="term" v={String(latest.term)} />
            <Row k="SQI" v={fmt3(latest.SQI)} />
            <Row k="ρ" v={fmt3(latest.rho)} />
            <Row k="Ī" v={fmt3(latest.iota)} />
            <Row k="ΔΦ" v={fmt3(latest.dphi)} />
            <Row k="⟲" v={fmt3(latest.eq)} />

            <div className="pt-2">
              <div className="mb-2 text-[11px] font-black tracking-widest text-gray-500 uppercase">Homeostasis ⟲</div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-black/10">
                <div className={`${eqTone} h-full transition-all duration-500`} style={{ width: `${Math.round(eq * 100)}%` }} />
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
                <span className="font-bold">{latest.locked === true ? "LOCKED" : latest.locked === false ? "UNLOCKED" : "—"}</span>
              </div>
              {latest.threshold != null ? <div className="mt-1 text-gray-500">thr={String(latest.threshold)}</div> : null}
              {latest.lock_id ? <div className="mt-1 text-gray-500">lock_id={String(latest.lock_id)}</div> : null}
            </div>
          </div>
        </div>

        {/* Live Feed */}
        <div className="lg:col-span-2 rounded-2xl border border-black/10 bg-white p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-xs font-black tracking-widest text-gray-500 uppercase">Live Feed</div>
              <div className="mt-1 font-mono text-[11px] text-gray-400">Buttons above (or CLI) emit events — they should appear here in realtime.</div>
            </div>
            <div className="font-mono text-[11px] text-gray-500">{items.length} events</div>
          </div>

          <div className="mt-4 max-h-[560px] overflow-auto rounded-xl border border-black/10 bg-slate-950/[0.04]">
            {items.length === 0 ? (
              <div className="p-4 font-mono text-xs text-gray-500">Waiting for events…</div>
            ) : (
              <ul className="divide-y divide-black/10">
                {items.map((it, idx) => (
                  <li key={`${it.ts}-${idx}`} className="p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-mono text-[11px] text-gray-500">{new Date(it.ts * 1000).toLocaleString()}</div>
                      <div className="rounded-full border border-black/10 bg-white px-2 py-0.5 font-mono text-[10px] font-bold">{String(it.kind)}</div>
                    </div>
                    <pre className="mt-3 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-white p-3 text-[11px] text-gray-700">
                      {JSON.stringify(it.payload, null, 2)}
                    </pre>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="mt-3 font-mono text-[11px] text-gray-500">
            If this feed is empty but your API health is OK, your backend may not be serving <span className="font-bold">{prefix}/qfc</span>.
          </div>
        </div>
      </div>
    </div>
  );
}

function Row(props: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-gray-500">{props.k}</span>
      <span className="font-bold">{props.v}</span>
    </div>
  );
}