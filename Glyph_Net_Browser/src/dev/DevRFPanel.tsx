import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

// You can set VITE_RADIO_BASE to "http://127.0.0.1:8787" if you are not proxying.
const RADIO_BASE: string = (import.meta as any)?.env?.VITE_RADIO_BASE || "";

// ---- Types -----------------------------------------------------
interface TransportListResp {
  ok: boolean;
  drivers: Array<{
    id: string;
    kind: string;
    up: boolean;
    [k: string]: any;
  }>;
  rfOutbox: number;
}

interface MockStatusResp {
  ok: boolean;
  enabled: boolean;
  config: MockCfg;
  drivers?: TransportListResp["drivers"];
  rfOutbox?: number;
}

type MockCfg = {
  enabled: boolean;
  loopback: boolean;
  delay_ms: number;
  jitter_ms: number;
  loss_pct: number; // 0..100
};

// ---- Helpers ---------------------------------------------------
async function jfetch<T = any>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(RADIO_BASE + path, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  const text = await r.text();
  let body: any = null;
  try { body = text ? JSON.parse(text) : {}; } catch { body = { ok: false, error: text || "bad json" }; }
  if (!r.ok) throw new Error(body?.error || r.statusText || "request failed");
  return body as T;
}

function b64(s: string) {
  if (typeof window === "undefined") return Buffer.from(s, "utf8").toString("base64");
  return window.btoa(unescape(encodeURIComponent(s)));
}

function cn(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

// ---- UI --------------------------------------------------------
export default function DevRFPanel() {
  const [drivers, setDrivers] = useState<TransportListResp["drivers"]>([]);
  const [rfOutbox, setRfOutbox] = useState(0);
  const [mock, setMock] = useState<MockCfg>({ enabled: false, loopback: false, delay_ms: 0, jitter_ms: 0, loss_pct: 0 });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Injector form
  const [topic, setTopic] = useState("personal:ucs://local/ucs_hub");
  const [ascii, setAscii] = useState("Hello from DevRFPanel 👋");
  const data_b64 = useMemo(() => b64(ascii), [ascii]);

  const pollRef = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    setErr(null);
    try {
      const [t, m] = await Promise.all([
        jfetch<TransportListResp>("/bridge/transports"),
        jfetch<MockStatusResp>("/dev/rf/mock/status"),
      ]);
      setDrivers(t.drivers || m.drivers || []);
      setRfOutbox(typeof t.rfOutbox === "number" ? t.rfOutbox : (m.rfOutbox || 0));
      setMock(m.config || { enabled: m.enabled, loopback: false, delay_ms: 0, jitter_ms: 0, loss_pct: 0 });
    } catch (e: any) {
      setErr(String(e?.message || e));
    }
  }, []);

  useEffect(() => {
    refresh();
    pollRef.current = window.setInterval(refresh, 2000);
    return () => { if (pollRef.current) window.clearInterval(pollRef.current); };
  }, [refresh]);

  const enableMock = useCallback(async () => {
    setBusy(true); setErr(null);
    try {
      const body = { loopback: mock.loopback, delay_ms: Number(mock.delay_ms)||0, jitter_ms: Number(mock.jitter_ms)||0, loss_pct: Number(mock.loss_pct)||0 };
      await jfetch("/dev/rf/mock/enable", { method: "POST", body: JSON.stringify(body) });
      await refresh();
    } catch (e: any) { setErr(String(e?.message || e)); } finally { setBusy(false); }
  }, [mock.loopback, mock.delay_ms, mock.jitter_ms, mock.loss_pct, refresh]);

  const disableMock = useCallback(async () => {
    setBusy(true); setErr(null);
    try { await jfetch("/dev/rf/mock/disable", { method: "POST" }); await refresh(); }
    catch (e: any) { setErr(String(e?.message || e)); }
    finally { setBusy(false); }
  }, [refresh]);

  const inject = useCallback(async () => {
    setBusy(true); setErr(null);
    try {
      await jfetch("/dev/rf/mock/rx", { method: "POST", body: JSON.stringify({ topic, data_b64 }) });
      await refresh();
    } catch (e: any) { setErr(String(e?.message || e)); } finally { setBusy(false); }
  }, [topic, data_b64, refresh]);

  const quickHello = useCallback(() => {
    setAscii("Hello over RF (mock loopback) ✨");
    setTimeout(inject, 0);
  }, [inject]);

  return (
    <div className="p-4 md:p-6 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-semibold">RF DevTools</h1>
          <p className="text-sm text-neutral-500">Control the mock RF link, inject frames, and view transport status.</p>
        </div>
        <button
          className={cn(
            "inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm shadow-sm",
            "bg-neutral-100 hover:bg-neutral-200 active:bg-neutral-300"
          )}
          onClick={refresh}
          disabled={busy}
          title="Refresh"
        >
          <span className="i-lucide-refresh-cw" /> Refresh
        </button>
      </header>

      {err && (
        <div className="rounded-xl border border-red-300 bg-red-50 text-red-700 p-3 text-sm">{err}</div>
      )}

      {/* Status cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-2xl border p-4 bg-white shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">Mock RF Link</h2>
            <span className={cn(
              "px-2 py-0.5 text-xs rounded-full",
              mock.enabled ? "bg-green-100 text-green-800" : "bg-neutral-100 text-neutral-700"
            )}>
              {mock.enabled ? "enabled" : "disabled"}
            </span>
          </div>

          <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" className="h-4 w-4" checked={mock.loopback} onChange={e => setMock(m => ({ ...m, loopback: e.target.checked }))} />
              Loopback
            </label>
            <label className="flex items-center gap-2">
              <input type="number" className="w-24 rounded-lg border px-2 py-1" min={0} value={mock.loss_pct}
                onChange={e => setMock(m => ({ ...m, loss_pct: Number(e.target.value)||0 }))} />
              <span className="text-neutral-500">loss %</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="number" className="w-24 rounded-lg border px-2 py-1" min={0} value={mock.delay_ms}
                onChange={e => setMock(m => ({ ...m, delay_ms: Number(e.target.value)||0 }))} />
              <span className="text-neutral-500">delay ms</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="number" className="w-24 rounded-lg border px-2 py-1" min={0} value={mock.jitter_ms}
                onChange={e => setMock(m => ({ ...m, jitter_ms: Number(e.target.value)||0 }))} />
              <span className="text-neutral-500">jitter ms</span>
            </label>
          </div>

          <div className="mt-4 flex items-center gap-2">
            {!mock.enabled ? (
              <button className="rounded-xl bg-green-600 text-white px-3 py-2 text-sm shadow hover:bg-green-700 disabled:opacity-50" disabled={busy} onClick={enableMock}>Enable</button>
            ) : (
              <>
                <button className="rounded-xl bg-neutral-800 text-white px-3 py-2 text-sm shadow hover:bg-black/80 disabled:opacity-50" disabled={busy} onClick={enableMock}>Apply</button>
                <button className="rounded-xl bg-neutral-100 px-3 py-2 text-sm shadow-sm hover:bg-neutral-200 disabled:opacity-50" disabled={busy} onClick={disableMock}>Disable</button>
              </>
            )}
          </div>
        </div>

        <div className="rounded-2xl border p-4 bg-white shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">Transports</h2>
            <span className="text-sm text-neutral-500">rfOutbox: {rfOutbox}</span>
          </div>
          <div className="mt-3 space-y-2">
            {drivers.map((d) => (
              <div key={d.id} className="flex items-center justify-between rounded-xl border px-3 py-2">
                <div>
                  <div className="font-mono text-sm">{d.id}</div>
                  <div className="text-xs text-neutral-500">{d.kind}</div>
                </div>
                <div className={cn("text-xs px-2 py-0.5 rounded-full", d.up ? "bg-emerald-100 text-emerald-700" : "bg-neutral-100 text-neutral-600")}>{d.up ? "up" : "down"}</div>
              </div>
            ))}
            {drivers.length === 0 && (
              <div className="text-sm text-neutral-500">No drivers registered yet.</div>
            )}
          </div>
        </div>

        <div className="rounded-2xl border p-4 bg-white shadow-sm">
          <h2 className="font-medium">Quick test</h2>
          <p className="text-sm text-neutral-500 mt-1">Sends a tiny Base64 payload to <span className="font-mono">{topic}</span> via <span className="font-mono">/dev/rf/mock/rx</span>.</p>
          <div className="mt-3 flex flex-col gap-2">
            <button className="rounded-xl bg-blue-600 text-white px-3 py-2 text-sm shadow hover:bg-blue-700 disabled:opacity-50" disabled={busy} onClick={quickHello}>Send “Hello”</button>
            <code className="text-xs text-neutral-500">data_b64 = {b64("Hello over RF (mock loopback) ✨")}</code>
          </div>
        </div>
      </section>

      {/* Injector form */}
      <section className="rounded-2xl border p-4 bg-white shadow-sm">
        <h2 className="font-medium">Injector</h2>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="block">
            <div className="text-sm text-neutral-600 mb-1">Topic (graph:recipient)</div>
            <input
              className="w-full rounded-xl border px-3 py-2 font-mono text-sm"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="personal:ucs://local/ucs_hub"
            />
          </label>
          <label className="block">
            <div className="text-sm text-neutral-600 mb-1">ASCII payload (auto Base64)</div>
            <input
              className="w-full rounded-xl border px-3 py-2 font-mono text-sm"
              value={ascii}
              onChange={(e) => setAscii(e.target.value)}
              placeholder="Hello"
            />
          </label>
          <label className="block md:col-span-2">
            <div className="text-sm text-neutral-600 mb-1">data_b64</div>
            <input
              className="w-full rounded-xl border px-3 py-2 font-mono text-xs"
              value={data_b64}
              readOnly
            />
          </label>
        </div>
        <div className="mt-4 flex items-center gap-2">
          <button className="rounded-xl bg-blue-600 text-white px-3 py-2 text-sm shadow hover:bg-blue-700 disabled:opacity-50" disabled={busy} onClick={inject}>Inject frame</button>
          <button className="rounded-xl bg-neutral-100 px-3 py-2 text-sm shadow-sm hover:bg-neutral-200 disabled:opacity-50" disabled={busy} onClick={refresh}>Refresh status</button>
        </div>
      </section>

      <footer className="text-xs text-neutral-500">
        Hints: enable Mock RF + Loopback to see frames echoed back as <span className="font-mono">(rf)</span> capsules on your WS subscriber for this topic.
        Endpoints used: <span className="font-mono">/dev/rf/mock/status</span>, <span className="font-mono">/dev/rf/mock/enable</span>, <span className="font-mono">/dev/rf/mock/disable</span>, <span className="font-mono">/dev/rf/mock/rx</span>, and <span className="font-mono">/bridge/transports</span>.
      </footer>
    </div>
  );
}
