// src/routes/BridgePanel.tsx
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

/**
 * WebSerial ↔ radio-node /ws/rflink adapter (ASCII base64 line mode).
 *
 * Device protocol (MVP):
 *   • TX to device: "B64:<base64-encoded RF frame bytes>\n"
 *   • RX from device: same line format; we parse header to extract topic/seq.
 *
 * RF frame layout (must match radio-node encodeFrame):
 *   [ver u8][seq u32 BE][ts u64 BE][codecLen u8][codec..][topicLen u8][topic..][payload..]
 *
 * WebSocket protocol to radio-node (/radio/ws/rflink?token=...):
 *   ← {type:"hello", mtu, rate_hz}
 *   ← {type:"tx", bytes_b64}
 *   → {type:"rx", topic, seq?, bytes_b64}
 */

declare global {
  interface Navigator {
    serial?: any;
  }
}

type HelloMsg = { type: "hello"; mtu: number; rate_hz: number };
type TxMsg = { type: "tx"; bytes_b64: string };
type RfRxMsg = { type: "rx"; topic: string; seq?: number; bytes_b64: string };

// Safe base64 helpers (TypeScript-friendly)
function b64ToU8(b64: string): Uint8Array {
  const bin = atob(b64);
  const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return u8;
}
function u8ToB64(u8: Uint8Array): string {
  let s = "";
  for (let i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]);
  return btoa(s);
}

function parseRFHeader(bytes: Uint8Array): {
  ok: boolean;
  topic?: string;
  seq?: number;
  ts?: number;
  codec?: string;
  payloadOffset?: number;
  err?: string;
} {
  try {
    if (bytes.length < 1 + 4 + 8 + 1 + 1) return { ok: false, err: "short" };
    let o = 0;
    const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);

    /* ver */ o += 1;
    const seq = dv.getUint32(o, false);
    o += 4;
    const tsHi = dv.getUint32(o, false);
    o += 4;
    const tsLo = dv.getUint32(o, false);
    o += 4;
    const ts = tsHi * 2 ** 32 + tsLo;

    const codecLen = bytes[o++];
    if (bytes.length < o + codecLen + 1) return { ok: false, err: "short(codec)" };
    const codec = new TextDecoder().decode(bytes.subarray(o, o + codecLen));
    o += codecLen;

    const topicLen = bytes[o++];
    if (bytes.length < o + topicLen) return { ok: false, err: "short(topic)" };
    const topic = new TextDecoder().decode(bytes.subarray(o, o + topicLen));
    o += topicLen;

    return { ok: true, topic, seq, ts, codec, payloadOffset: o };
  } catch (e: any) {
    return { ok: false, err: String(e?.message || e) };
  }
}

// Line reader for WebSerial (\n-terminated ASCII)
class LineReader {
  private decoder = new TextDecoder();
  private buf = "";
  feed(chunk: Uint8Array): string[] {
    this.buf += this.decoder.decode(chunk, { stream: true });
    const out: string[] = [];
    for (;;) {
      const i = this.buf.indexOf("\n");
      if (i < 0) break;
      out.push(this.buf.slice(0, i).replace(/\r$/, ""));
      this.buf = this.buf.slice(i + 1);
    }
    return out;
  }
}

function wsURL(token: string) {
  const search = new URLSearchParams({ token });
  // Relative path so Vite proxy sends to :8787 in dev
  return `/radio/ws/rflink?${search.toString()}`;
}

function useLocalStorage<T>(key: string, initial: T) {
  const [val, setVal] = useState<T>(() => {
    try {
      const v = localStorage.getItem(key);
      return v ? (JSON.parse(v) as T) : initial;
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(val));
    } catch {}
  }, [key, val]);
  return [val, setVal] as const;
}

export default function BridgePanel() {
  const [bridgeToken, setBridgeToken] = useLocalStorage<string>("gnet:bridgeToken", "dev-bridge");
  const [baud, setBaud] = useLocalStorage<number>("gnet:serialBaud", 115200);
  const [hello, setHello] = useState<HelloMsg | null>(null);
  const [health, setHealth] = useState<any | null>(null);

  const [wsConnected, setWsConnected] = useState(false);
  const [serialConnected, setSerialConnected] = useState(false);

  const [txFrames, setTxFrames] = useState(0); // → device
  const [rxFrames, setRxFrames] = useState(0); // ← device
  const [txBytes, setTxBytes] = useState(0);
  const [rxBytes, setRxBytes] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const serialPortRef = useRef<any>(null);
  const serialWriterRef = useRef<any>(null);
  const serialReaderRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const lineReaderRef = useRef<LineReader | null>(null);

  const canSerial = !!navigator.serial;

  // ---- WS connect/disconnect ----
  const connectWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    const ws = new WebSocket(wsURL(bridgeToken));
    wsRef.current = ws;

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => {
      setWsConnected(false);
      wsRef.current = null;
    };
    ws.onerror = () => {
      setWsConnected(false);
    };

    ws.onmessage = async (ev) => {
      try {
        const j = JSON.parse(String(ev.data)) as HelloMsg | TxMsg | any;
        if (j?.type === "hello") {
          setHello(j as HelloMsg);
          return;
        }
        if (j?.type === "tx" && typeof j.bytes_b64 === "string") {
          const bytes = b64ToU8(j.bytes_b64);
          await writeToDevice(bytes);
          setTxFrames((v) => v + 1);
          setTxBytes((v) => v + bytes.length);
        }
      } catch {}
    };
  }, [bridgeToken]);

  const disconnectWS = useCallback(() => {
    try {
      wsRef.current?.close(1000, "manual");
    } catch {}
    wsRef.current = null;
    setWsConnected(false);
  }, []);

  // ---- Bridge health check (HTTP) ----
  const checkBridge = useCallback(async () => {
    try {
      const r = await fetch("/radio/bridge/health", {
        headers: { "X-Bridge-Token": bridgeToken },
      });
      const j = await r.json();
      setHealth({ ok: r.ok, ...j });
    } catch (e: any) {
      setHealth({ ok: false, error: String(e?.message || e) });
    }
  }, [bridgeToken]);

  // ---- Serial connect/disconnect ----
  const connectSerial = useCallback(async () => {
    if (!canSerial) return alert("WebSerial not available (try Chrome over HTTPS or localhost).");
    if (serialPortRef.current) return;
    try {
      const port = await navigator.serial!.requestPort();
      await port.open({ baudRate: baud });
      serialPortRef.current = port;
      serialWriterRef.current = port.writable.getWriter();
      serialReaderRef.current = port.readable.getReader();
      lineReaderRef.current = new LineReader();
      setSerialConnected(true);
      readSerialLoop(); // fire-and-forget
    } catch (e: any) {
      alert(`Serial error: ${e?.message || e}`);
    }
  }, [baud, canSerial]);

  const disconnectSerial = useCallback(async () => {
    try {
      await serialReaderRef.current?.cancel();
    } catch {}
    try {
      serialReaderRef.current?.releaseLock();
    } catch {}
    serialReaderRef.current = null;
    lineReaderRef.current = null;

    try {
      await serialWriterRef.current?.close();
    } catch {}
    try {
      serialWriterRef.current?.releaseLock();
    } catch {}
    serialWriterRef.current = null;

    try {
      await serialPortRef.current?.close();
    } catch {}
    serialPortRef.current = null;

    setSerialConnected(false);
  }, []);

  async function writeToDevice(bytes: Uint8Array) {
    const encoder = new TextEncoder();
    const line = `B64:${u8ToB64(bytes)}\n`;
    await serialWriterRef.current?.write(encoder.encode(line));
  }

  async function readSerialLoop() {
    for (;;) {
      try {
        const { value, done } = await serialReaderRef.current!.read();
        if (done) break;
        if (!value) continue;
        const lines = lineReaderRef.current!.feed(value);
        for (const line of lines) {
          if (!line.startsWith("B64:")) continue;
          const b64 = line.slice(4).trim();
          if (!b64) continue;
          const bytes = b64ToU8(b64);
          setRxBytes((v) => v + bytes.length);
          setRxFrames((v) => v + 1);

          const h = parseRFHeader(bytes);
          if (!h.ok || !h.topic) continue; // malformed

          const msg: RfRxMsg = { type: "rx", topic: h.topic!, bytes_b64: u8ToB64(bytes) };
          if (typeof h.seq === "number") msg.seq = h.seq;

          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(msg));
          }
        }
      } catch {
        break;
      }
    }
  }

  useEffect(() => {
    return () => {
      try {
        wsRef.current?.close(1000);
      } catch {}
      disconnectSerial();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const status = useMemo(() => {
    const a = wsConnected ? "🟢 RF-link WS" : "⚪ RF-link WS";
    const b = serialConnected ? "🟢 Serial" : "⚪ Serial";
    const c = hello ? `• MTU ${hello.mtu} • ${hello.rate_hz} Hz` : "";
    return `${a} • ${b} ${c}`;
  }, [wsConnected, serialConnected, hello]);

  return (
    <div className="p-4 max-w-3xl mx-auto space-y-4">
      <h1 className="text-xl font-semibold">RF Bridge (WebSerial ↔ radio-node)</h1>

      <div className="text-sm p-3 rounded border bg-black/5">{status}</div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="p-3 rounded border">
          <div className="font-medium mb-2">Bridge Auth</div>
          <label className="text-sm block mb-1">X-Bridge-Token</label>
          <input
            className="w-full px-2 py-1 rounded border"
            value={bridgeToken}
            onChange={(e) => setBridgeToken(e.target.value)}
            placeholder="dev-bridge"
          />
          <div className="mt-2 flex gap-2 flex-wrap">
            {!wsConnected ? (
              <button className="px-3 py-1 rounded bg-blue-600 text-white" onClick={connectWS}>
                Connect WS
              </button>
            ) : (
              <button className="px-3 py-1 rounded bg-neutral-700 text-white" onClick={disconnectWS}>
                Disconnect WS
              </button>
            )}
            <button className="px-3 py-1 rounded border" onClick={checkBridge}>
              Check Bridge Health
            </button>
          </div>
          {health && (
            <pre className="mt-2 text-xs bg-black/5 rounded p-2 overflow-auto">
{JSON.stringify(health, null, 2)}
            </pre>
          )}
          <p className="text-xs text-neutral-500 mt-2">
            Uses relative URL <code>/radio/ws/rflink?token=…</code> and <code>/radio/bridge/health</code> (Vite proxy → :8787).
          </p>
        </div>

        <div className="p-3 rounded border">
          <div className="font-medium mb-2">Serial</div>
          <label className="text-sm block mb-1">Baud</label>
          <input
            className="w-full px-2 py-1 rounded border"
            type="number"
            value={baud}
            onChange={(e) => setBaud(parseInt(e.target.value || "115200", 10))}
          />
          <div className="mt-2 flex gap-2">
            {!serialConnected ? (
              <button
                className="px-3 py-1 rounded bg-green-600 text-white"
                onClick={connectSerial}
                disabled={!canSerial}
                title={!canSerial ? "WebSerial not supported in this browser" : "Connect to serial device"}
              >
                {canSerial ? "Connect Serial" : "WebSerial not supported"}
              </button>
            ) : (
              <button className="px-3 py-1 rounded bg-neutral-700 text-white" onClick={disconnectSerial}>
                Disconnect Serial
              </button>
            )}
          </div>
          <p className="text-xs text-neutral-500 mt-2">
            Device must speak ASCII line mode: <code>B64:&lt;base64&gt;</code>
          </p>
        </div>
      </div>

      <div className="p-3 rounded border grid grid-cols-2 gap-2">
        <div>
          <div className="text-sm text-neutral-600">→ Device (TX)</div>
          <div className="text-2xl font-mono">{txFrames}</div>
          <div className="text-xs text-neutral-500">{txBytes} bytes</div>
        </div>
        <div>
          <div className="text-sm text-neutral-600">← Device (RX)</div>
          <div className="text-2xl font-mono">{rxFrames}</div>
          <div className="text-xs text-neutral-500">{rxBytes} bytes</div>
        </div>
      </div>

      <div className="text-xs text-neutral-500">
        Tip: Set <code>RADIO_BRIDGE_TOKEN</code> in <code>radio-node/.env.local</code> to match the token above.
      </div>
    </div>
  );
}