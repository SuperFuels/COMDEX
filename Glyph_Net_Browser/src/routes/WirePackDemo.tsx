// WirePackDemo.tsx  (FULL FILE REPLACEMENT)
// Demo shell (tabs + dropdown) + v46 Transport streaming benchmark (real endpoints)

import React, { useEffect, useMemo, useRef, useState } from "react";
import { V44SqlOnStreamsDemo } from "./protocols/V44SqlOnStreamsDemo";
import { V38TrustReceiptsDemo } from "./protocols/V38TrustReceiptsDemo";
import { V45CrossLanguageVectorsDemo } from "./protocols/V45CrossLanguageVectorsDemo";
import { V32HeavyHittersDemo } from "./protocols/V32HeavyHittersDemo";
import { V10StreamingTransportDemo } from "./protocols/V10StreamingTransportDemo";
import { V29ProjectionDemo } from "./protocols/V29ProjectionDemo";
import { V30SumOverQDemo } from "./protocols/V30SumOverQDemo";
import { V33RangeSumsDemo } from "./protocols/V33RangeSumsDemo";
import { V41ReceiptGatedQueriesDemo } from "./protocols/V41ReceiptGatedQueriesDemo";
// -------------------------------
// Shared helpers
// -------------------------------

function fmtKB(n: number) {
  return `${(n / 1024).toFixed(2)} KB`;
}

function ratio(a: number, b: number) {
  if (a <= 0) return "—";
  return (b / a).toFixed(2) + "×";
}

function projectTotals(templateBytes: number, avgDeltaBytes: number, gzAvgBytes: number, frames: number) {
  const wire = templateBytes + avgDeltaBytes * frames;
  const gz = gzAvgBytes * frames;
  const pctSmaller = gz > 0 ? (1 - wire / gz) * 100 : 0;
  return { wire, gz, pctSmaller };
}

function bytes(n: number) {
  const units = ["B", "KB", "MB", "GB"];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
}

function pct(before: number, after: number) {
  if (before <= 0) return "—";
  const r = 100 * (1 - after / before);
  return `${r.toFixed(1)}%`;
}

function withTimeout<T>(p: Promise<T>, ms: number, label: string): Promise<T> {
  return Promise.race([
    p,
    new Promise<T>((_, rej) => setTimeout(() => rej(new Error(`${label} timed out (${ms}ms)`)), ms)),
  ]);
}

async function fetchJsonWithTimeout(url: string, init: RequestInit = {}, timeoutMs = 8000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, { ...init, signal: ctrl.signal });
    const txt = await r.text();
    let json: any = {};
    try {
      json = txt ? JSON.parse(txt) : {};
    } catch {
      json = { _nonJson: true, _text: txt.slice(0, 200) };
    }
    return { ok: r.ok, status: r.status, json };
  } finally {
    clearTimeout(t);
  }
}

function toU8(s: string) {
  return new TextEncoder().encode(s);
}
function fromU8(u8: Uint8Array) {
  return new TextDecoder().decode(u8);
}

// ---------- JSON canonicalization ----------
function stableStringify(x: any): string {
  const seen = new WeakSet<object>();
  const walk = (v: any): any => {
    if (v === null || typeof v !== "object") return v;
    if (seen.has(v)) throw new Error("cyclic json");
    seen.add(v);

    if (Array.isArray(v)) return v.map(walk);
    const out: any = {};
    for (const k of Object.keys(v).sort()) out[k] = walk(v[k]);
    return out;
  };
  return JSON.stringify(walk(x));
}

function canonText(text: string): { canon: string; isJson: boolean } {
  try {
    const obj = JSON.parse(text);
    return { canon: stableStringify(obj), isJson: true };
  } catch {
    return { canon: text ?? "", isJson: false };
  }
}

// ---------- gzip helpers (Blob-safe) ----------
async function gzipCompress(u8: Uint8Array): Promise<Uint8Array> {
  const bytesCopy = new Uint8Array(u8);
  const stream = new Blob([bytesCopy]).stream().pipeThrough(new CompressionStream("gzip"));
  const out = await new Response(stream).arrayBuffer();
  return new Uint8Array(out);
}
async function gzipDecompress(u8: Uint8Array): Promise<Uint8Array> {
  const bytesCopy = new Uint8Array(u8);
  const stream = new Blob([bytesCopy]).stream().pipeThrough(new DecompressionStream("gzip"));
  const out = await new Response(stream).arrayBuffer();
  return new Uint8Array(out);
}

// -------------------------------
// WirePack v46 endpoints (real backend)
// -------------------------------

async function wpSessionNew() {
  const { ok, status, json } = await fetchJsonWithTimeout("/api/wirepack/v46/session/new", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!ok) throw new Error(`session/new HTTP ${status}: ${JSON.stringify(json)}`);
  const sid = String(json?.session_id || "");
  if (!sid) throw new Error("session/new: missing session_id");
  return sid;
}

async function wpEncodeStruct(session_id: string, json_text: string) {
  const { ok, status, json } = await fetchJsonWithTimeout("/api/wirepack/v46/encode_struct", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id, json_text }),
  });
  if (!ok) throw new Error(`encode_struct HTTP ${status}: ${JSON.stringify(json)}`);
  return {
    kind: String(json?.kind || ""),
    bytes_out: Number(json?.bytes_out || 0),
    encoded_b64: String(json?.encoded_b64 || ""),
  };
}

async function wpDecodeStruct(session_id: string, encoded_b64: string) {
  const { ok, status, json } = await fetchJsonWithTimeout("/api/wirepack/v46/decode_struct", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id, encoded_b64 }),
  });
  if (!ok) throw new Error(`decode_struct HTTP ${status}: ${JSON.stringify(json)}`);
  return {
    kind: String(json?.kind || ""),
    decoded_text: String(json?.decoded_text || ""),
  };
}

// -------------------------------
// Demo shell (tabs + dropdown)
// -------------------------------

type TabId = "transport" | "analytics" | "trust";
type DemoId =
  | "v46_transport_streaming"
  | "v44_sql_on_streams"
  | "v32_heavy_hitters"
  | "v38_trust_receipts"
  | "v41_receipt_gated_queries"
  | "v10_streaming_transport"
  | "v45_cross_language_vectors"
  | "v29_projection_q"
  | "v30_sum_over_q"
  | "v33_range_sums";
 

type DemoMeta = {
  id: DemoId;
  tab: TabId;
  title: string;
  blurb: string;
  Component: React.FC;
};

function TabButton(props: { active: boolean; onClick: () => void; children: any }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      style={{
        padding: "6px 10px",
        borderRadius: 999,
        border: "1px solid " + (props.active ? "#111827" : "#e5e7eb"),
        background: props.active ? "#111827" : "#fff",
        color: props.active ? "#fff" : "#111827",
        fontSize: 11,
        fontWeight: 700,
        cursor: "pointer",
      }}
    >
      {props.children}
    </button>
  );
}

function ComingSoon(props: { title: string; bullets: string[] }) {
  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ fontSize: 13, fontWeight: 800, color: "#111827" }}>{props.title}</div>
      <div style={{ fontSize: 11, color: "#6b7280", marginTop: 6 }}>
        This tab is wired for a real demo component. Drop the real implementation in and keep the shell unchanged.
      </div>
      <ul style={{ marginTop: 10, marginBottom: 0, paddingLeft: 16, fontSize: 11, color: "#374151" }}>
        {props.bullets.map((b) => (
          <li key={b} style={{ marginBottom: 6 }}>
            {b}
          </li>
        ))}
      </ul>
    </div>
  );
}

// -------------------------------
// v46 demo component
// -------------------------------

type DemoCaseId = "http" | "sql" | "iot" | "delta_stream";

function makeDeltaStreamSample() {
  const baseHeaders = Array.from({ length: 120 }).map((_, i) => ({
    k: `x-glyph-header-${i}`,
    v: `token=${"abc123".repeat(6)}; scope=read:all; region=eu-west-1; trace=000`,
  }));

  const frames = Array.from({ length: 220 }).map((_, i) => {
    const tr = String(i % 1000).padStart(3, "0");
    const seq6 = String(i).padStart(6, "0");
    const ck3 = String(i % 1000).padStart(3, "0");

    const headers = baseHeaders.map((h) =>
      h.k === "x-glyph-header-0"
        ? { ...h, v: `token=${"abc123".repeat(6)}; scope=read:all; region=eu-west-1; trace=${tr}` }
        : h,
    );

    return {
      t: 1700000000000 + i * 200,
      method: "GET",
      path: "/api/v1/search?q=glyphos+wirepack+v46",
      headers,
      body: null,
      _zz_seq: seq6,
      _zz_note: `checkpoint=${ck3}`,
    };
  });

  return JSON.stringify({ stream: "delta.frames", base: { method: "GET", path: "/api/v1/search?q=glyphos+wirepack+v46" }, frames }, null, 2);
}

function patchTraceHeader(headers: any[], tr3: string) {
  if (!Array.isArray(headers)) return;
  const idx = headers.findIndex((h) => h && typeof h === "object" && h.k === "x-glyph-header-0");
  if (idx >= 0) {
    const h = headers[idx];
    h.v = String(h.v || "").replace(/trace=\d+/g, `trace=${tr3}`);
  }
}

function buildStreamFrames(caseId: DemoCaseId, payloadText: string, framesN: number) {
  const { canon, isJson } = canonText(payloadText);

  if (!isJson) {
    const base = String(payloadText ?? "");
    return Array.from({ length: framesN }).map((_, i) => `${base}\n#frame=${String(i).padStart(6, "0")}`);
  }

  const baseObj: any = JSON.parse(canon);

  if (Array.isArray(baseObj?.frames) && baseObj.frames.length) {
    const frames = baseObj.frames.slice(0, Math.max(1, framesN)).map((f: any, i: number) => {
      const out = { ...(f || {}) };

      const tr3 = String(i % 1000).padStart(3, "0");
      const seq6 = String(i).padStart(6, "0");
      const ck3 = String(i % 1000).padStart(3, "0");

      out.t = typeof out.t === "number" ? out.t + i : 1700000000000 + i * 200;
      patchTraceHeader(out.headers, tr3);

      out._zz_seq = seq6;
      out._zz_note = `checkpoint=${ck3}`;

      delete out.seq;
      delete out.note;
      delete out.trace;

      return out;
    });

    const restBase: any = { ...baseObj };
    delete restBase.frames;

    return frames.map((frame: any, i: number) =>
      stableStringify({
        ...restBase,
        frame,
        _zz_i: String(i).padStart(6, "0"),
      }),
    );
  }

  return Array.from({ length: framesN }).map((_, i) => {
    const o = typeof structuredClone === "function" ? structuredClone(baseObj) : JSON.parse(JSON.stringify(baseObj));

    const tr3 = String(i % 1000).padStart(3, "0");
    const seq6 = String(i).padStart(6, "0");
    const ck3 = String(i % 1000).padStart(3, "0");

    o.t = typeof o.t === "number" ? (o.t ?? 1700000000000) + i : 1700000000000 + i;
    patchTraceHeader(o.headers, tr3);

    if (caseId === "sql") o._zz_batch = String(i).padStart(6, "0");
    if (caseId === "iot") o._zz_tick = String(i).padStart(6, "0");

    o._zz_seq = seq6;
    o._zz_note = `checkpoint=${ck3}`;

    delete o.seq;
    delete o.note;
    delete o.trace;

    return stableStringify(o);
  });
}

const TransportV46Demo: React.FC = () => {
  const [caseId, setCaseId] = useState<DemoCaseId>("http");
  const [payload, setPayload] = useState<string>("");

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const [mode, setMode] = useState<"single" | "stream">("stream");
  const [seconds, setSeconds] = useState<number>(15);
  const [hz, setHz] = useState<number>(10);

  const [rawCanonBytes, setRawCanonBytes] = useState<number | null>(null);
  const [tmplBytesOut, setTmplBytesOut] = useState<number | null>(null);
  const [deltaBytesOut, setDeltaBytesOut] = useState<number | null>(null);
  const [wireOk, setWireOk] = useState<boolean | null>(null);

  const [gzipBytesOut, setGzipBytesOut] = useState<number | null>(null);
  const [gzipOk, setGzipOk] = useState<boolean | null>(null);

  const [framesPlanned, setFramesPlanned] = useState<number | null>(null);
  const [framesSent, setFramesSent] = useState<number | null>(null);

  const [wireTemplateBytes, setWireTemplateBytes] = useState<number | null>(null);
  const [wireDeltaTotalBytes, setWireDeltaTotalBytes] = useState<number | null>(null);
  const [wireAvgDeltaBytes, setWireAvgDeltaBytes] = useState<number | null>(null);
  const [wireTotalBytes, setWireTotalBytes] = useState<number | null>(null);

  const [gzipTotalBytes, setGzipTotalBytes] = useState<number | null>(null);
  const [gzipAvgBytes, setGzipAvgBytes] = useState<number | null>(null);

  const [streamRoundtripOk, setStreamRoundtripOk] = useState<boolean | null>(null);

  const cancelRef = useRef(false);
  const didInitRef = useRef(false);

  const sample = useMemo(() => {
    if (caseId === "http") {
      const headers = Array.from({ length: 180 }).map((_, i) => ({
        k: `x-glyph-header-${i}`,
        v: `token=${"abc123".repeat(8)}; scope=read:all; region=eu-west-1; trace=${i}`,
      }));
      return JSON.stringify(
        { method: "GET", path: "/api/v1/search?q=glyphos+wirepack+v46", headers, body: null, trace: 0, t: 1700000000000 },
        null,
        2,
      );
    }

    if (caseId === "sql") {
      const rows = Array.from({ length: 1200 }).map((_, i) => ({
        id: i + 1,
        user_id: (i % 37) + 1,
        status: ["PENDING", "PAID", "FAILED"][i % 3],
        amount: (i % 97) * 1.25,
        currency: "EUR",
        region: "EU",
        note: `invoice=${Math.floor(i / 3)}; batch=v46; kind=settlement`,
      }));
      return JSON.stringify({ table: "payments", op: "INSERT_BULK", rows, trace: 0, t: 1700000000000 }, null, 0);
    }

    if (caseId === "iot") {
      const readings = Array.from({ length: 2400 }).map((_, i) => ({
        t: 1700000000000 + i * 250,
        device: `dev_${(i % 24) + 1}`,
        temp_c: 18.5 + (i % 7) * 0.1,
        hum: 0.45 + (i % 11) * 0.01,
        vib: (i % 5) * 0.02,
        flags: { ok: true, cal: i % 120 === 0 },
      }));
      return JSON.stringify({ stream: "iot.telemetry", readings, trace: 0, t: 1700000000000 }, null, 0);
    }

    return makeDeltaStreamSample();
  }, [caseId]);

  useEffect(() => {
    // only auto-load once to avoid overwriting edits
    if (!didInitRef.current) {
      setPayload(sample);
      didInitRef.current = true;
    }
  }, [sample]);

  function resetStats() {
    setErr(null);
    setNote(null);

    setRawCanonBytes(null);
    setTmplBytesOut(null);
    setDeltaBytesOut(null);
    setWireOk(null);
    setGzipBytesOut(null);
    setGzipOk(null);

    setFramesPlanned(null);
    setFramesSent(null);

    setWireTemplateBytes(null);
    setWireDeltaTotalBytes(null);
    setWireAvgDeltaBytes(null);
    setWireTotalBytes(null);

    setGzipTotalBytes(null);
    setGzipAvgBytes(null);

    setStreamRoundtripOk(null);
  }

  function loadSample() {
    setPayload(sample);
    resetStats();
  }

  async function runSingle() {
    const canon0 = canonText(payload || "").canon;
    const frames = buildStreamFrames(caseId, canon0, 2);
    const canon1 = canonText(frames[1]).canon;

    setRawCanonBytes(toU8(canon0).length);

    const sid = await withTimeout(wpSessionNew(), 8000, "session/new");
    const a = await withTimeout(wpEncodeStruct(sid, canon0), 15000, "encode_struct(template)");
    setTmplBytesOut(a.bytes_out);

    const b = await withTimeout(wpEncodeStruct(sid, canon1), 15000, "encode_struct(delta)");
    setDeltaBytesOut(b.bytes_out);

    const d = await withTimeout(wpDecodeStruct(sid, b.encoded_b64), 15000, "decode_struct");
    setWireOk(d.decoded_text === canon1);

    const gz = await withTimeout(gzipCompress(toU8(canon0)), 5000, "gzip compress");
    setGzipBytesOut(gz.length);

    const back = await withTimeout(gzipDecompress(gz), 5000, "gzip decompress");
    setGzipOk(fromU8(back) === canon0);
  }

  async function runStream() {
    cancelRef.current = false;

    const canon0 = canonText(payload || "").canon;
    const framesN = Math.max(2, Math.floor(seconds * hz));
    const frames = buildStreamFrames(caseId, canon0, framesN);

    setFramesPlanned(framesN);
    setFramesSent(0);

    let gzipTotal = 0;
    let tmplBytes = 0;
    let deltaTotal = 0;

    let lastEncodedB64 = "";
    const sid = await withTimeout(wpSessionNew(), 8000, "session/new");

    for (let i = 0; i < frames.length; i++) {
      if (cancelRef.current) break;

      const frameText = canonText(frames[i]).canon;

      try {
        const gz = await withTimeout(gzipCompress(toU8(frameText)), 7000, "gzip compress");
        gzipTotal += gz.length;
      } catch {
        setNote("note: gzip failed on at least one frame (browser/runtime limitation).");
      }

      const enc = await withTimeout(
        wpEncodeStruct(sid, frameText),
        15000,
        i === 0 ? "encode_struct(template)" : "encode_struct(delta)",
      );

      if (i === 0) {
        tmplBytes = enc.bytes_out;
        setWireTemplateBytes(tmplBytes);
      } else {
        deltaTotal += enc.bytes_out;
      }

      lastEncodedB64 = enc.encoded_b64;

      if (i % 10 === 0 || i === frames.length - 1) {
        setFramesSent(i + 1);
        setWireDeltaTotalBytes(deltaTotal);
        setWireTotalBytes(tmplBytes + deltaTotal);
        setGzipTotalBytes(gzipTotal);
      }
    }

    const deltasCount = Math.max(1, frames.length - 1);

    setWireDeltaTotalBytes(deltaTotal);
    setWireAvgDeltaBytes(Math.round(deltaTotal / deltasCount));
    setWireTotalBytes(tmplBytes + deltaTotal);

    setGzipTotalBytes(gzipTotal);
    setGzipAvgBytes(Math.round(gzipTotal / Math.max(1, frames.length)));

    try {
      if (sid && lastEncodedB64) {
        const dec = await withTimeout(wpDecodeStruct(sid, lastEncodedB64), 15000, "decode_struct(last)");
        const lastFrameCanon = canonText(frames[Math.max(0, frames.length - 1)]).canon;
        setStreamRoundtripOk(dec.decoded_text === lastFrameCanon);
      } else {
        setStreamRoundtripOk(null);
      }
    } catch {
      setStreamRoundtripOk(null);
      setNote((n) => n || "note: decode_struct(last) failed (stream stats still valid).");
    }
  }

  async function run() {
    if (busy) return;
    setBusy(true);
    resetStats();

    try {
      if (mode === "single") await runSingle();
      else await runStream();
    } catch (e: any) {
      setErr(e?.message || "Demo failed");
    } finally {
      setBusy(false);
      cancelRef.current = false;
    }
  }

  function cancel() {
    cancelRef.current = true;
    setBusy(false);
    setNote("cancelled");
  }

  const canShowSell =
    mode === "stream" &&
    framesSent != null &&
    wireTemplateBytes != null &&
    wireDeltaTotalBytes != null &&
    wireAvgDeltaBytes != null &&
    wireTotalBytes != null &&
    gzipTotalBytes != null &&
    gzipAvgBytes != null;

  const framesSafe = framesSent ?? 0;
  const tmplSafe = wireTemplateBytes ?? 0;
  const deltasSafe = wireDeltaTotalBytes ?? 0;
  const avgDeltaSafe = wireAvgDeltaBytes ?? 0;
  const wireTotalSafe = wireTotalBytes ?? 0;
  const gzTotalSafe = gzipTotalBytes ?? 0;
  const gzAvgSafe = gzipAvgBytes ?? 0;

  const smaller = gzTotalSafe > 0 ? wireTotalSafe < gzTotalSafe : false;
  const pctSmaller = gzTotalSafe > 0 ? (1 - wireTotalSafe / gzTotalSafe) * 100 : 0;

  const badgeBg = smaller ? "#ecfdf5" : "#fef2f2";
  const badgeFg = smaller ? "#065f46" : "#991b1b";
  const badgeBorder = smaller ? "#a7f3d0" : "#fecaca";

  const proj1k = canShowSell ? projectTotals(tmplSafe, avgDeltaSafe, gzAvgSafe, 1000) : null;
  const proj10k = canShowSell ? projectTotals(tmplSafe, avgDeltaSafe, gzAvgSafe, 10_000) : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, minHeight: "60vh" }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 800, color: "#111827" }}>
            v46 — Streaming transport (template once + deltas)
          </div>
          <div style={{ fontSize: 11, color: "#6b7280" }}>
            <b>Streaming</b>: template once + deltas across many frames (compared to <b>gzip-per-frame</b>).{" "}
            <b>Single</b>: template + one delta.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
          <select
            value={caseId}
            onChange={(e) => setCaseId(e.target.value as DemoCaseId)}
            style={{ padding: "6px 10px", borderRadius: 999, border: "1px solid #e5e7eb", background: "#fff", fontSize: 11 }}
          >
            <option value="http">Internet traffic (HTTP-ish)</option>
            <option value="sql">SQL bulk rows</option>
            <option value="iot">IoT telemetry stream</option>
            <option value="delta_stream">Delta stream (WirePack-favoring)</option>
          </select>

          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as any)}
            style={{ padding: "6px 10px", borderRadius: 999, border: "1px solid #e5e7eb", background: "#fff", fontSize: 11 }}
          >
            <option value="stream">Streaming benchmark</option>
            <option value="single">Single message</option>
          </select>

          {mode === "stream" ? (
            <>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
                sec
                <input
                  type="number"
                  value={seconds}
                  min={5}
                  max={120}
                  onChange={(e) => setSeconds(Math.max(5, Math.min(120, Number(e.target.value) || 15)))}
                  style={{ width: 70, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
                />
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
                Hz
                <input
                  type="number"
                  value={hz}
                  min={1}
                  max={60}
                  onChange={(e) => setHz(Math.max(1, Math.min(60, Number(e.target.value) || 10)))}
                  style={{ width: 70, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
                />
              </label>
            </>
          ) : null}

          <button
            type="button"
            onClick={loadSample}
            style={{ padding: "6px 10px", borderRadius: 999, border: "1px solid #e5e7eb", background: "#f9fafb", fontSize: 11, cursor: "pointer" }}
          >
            Load sample
          </button>

          {!busy ? (
            <button
              type="button"
              onClick={run}
              style={{ padding: "6px 12px", borderRadius: 999, border: "1px solid #111827", background: "#111827", color: "#f9fafb", fontSize: 11, fontWeight: 800, cursor: "pointer" }}
            >
              Run
            </button>
          ) : (
            <button
              type="button"
              onClick={cancel}
              style={{ padding: "6px 12px", borderRadius: 999, border: "1px solid #b91c1c", background: "#b91c1c", color: "#fff", fontSize: 11, fontWeight: 800, cursor: "pointer" }}
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {err ? <div style={{ fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}
      {note ? <div style={{ fontSize: 11, color: "#6b7280" }}>{note}</div> : null}

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: 10, minHeight: 0 }}>
        {/* LEFT */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, minHeight: 0 }}>
          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", overflow: "hidden", display: "flex", flexDirection: "column", minHeight: 260 }}>
            <div style={{ padding: 10, borderBottom: "1px solid #e5e7eb", fontSize: 11, color: "#6b7280" }}>Payload (edit if you want)</div>
            <textarea
              value={payload}
              onChange={(e) => setPayload(e.target.value)}
              style={{ flex: 1, border: "none", outline: "none", padding: 10, fontSize: 11, fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace", resize: "none", minHeight: 220 }}
            />
          </div>

          {canShowSell ? (
            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Streaming result (real measured numbers)</div>
                <div style={{ padding: "6px 10px", borderRadius: 999, border: `1px solid ${badgeBorder}`, background: badgeBg, color: badgeFg, fontSize: 11, fontWeight: 900, display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 14 }}>{smaller ? "✅" : "⚠️"}</span>
                  {smaller ? `WirePack is ${pctSmaller.toFixed(1)}% smaller 🚀` : `WirePack is ${Math.abs(pctSmaller).toFixed(1)}% larger`}
                </div>
              </div>

              <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10, background: "#fff" }}>
                  <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>WirePack v46</div>
                  <div style={{ fontSize: 11, color: "#374151", marginTop: 6 }}>
                    Frames: <b>{framesSafe}</b>
                  </div>
                  <div style={{ fontSize: 11, color: "#374151", marginTop: 8 }}>
                    Template: <b>{fmtKB(tmplSafe)}</b> <span style={{ color: "#6b7280" }}>({tmplSafe} B)</span>
                  </div>
                  <div style={{ fontSize: 11, color: "#374151", marginTop: 6 }}>
                    Deltas: <b>{fmtKB(deltasSafe)}</b>{" "}
                    <span style={{ color: "#6b7280" }}>
                      ({deltasSafe} B, avg <b>{avgDeltaSafe} B/frame</b>)
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: "#374151", marginTop: 6 }}>
                    Total: <b>{fmtKB(wireTotalSafe)}</b> <span style={{ color: "#6b7280" }}>({wireTotalSafe} B)</span>
                  </div>
                </div>

                <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10, background: "#fff" }}>
                  <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>gzip baseline (per-frame)</div>
                  <div style={{ fontSize: 11, color: "#374151", marginTop: 6 }}>
                    Total: <b>{fmtKB(gzTotalSafe)}</b> <span style={{ color: "#6b7280" }}>({gzTotalSafe} B)</span>
                  </div>
                  <div style={{ fontSize: 11, color: "#374151", marginTop: 6 }}>
                    Avg/frame: <b>{gzAvgSafe} B</b>
                  </div>
                  <div style={{ fontSize: 11, color: "#374151", marginTop: 10 }}>
                    WirePack vs gzip: <b style={{ color: smaller ? "#065f46" : "#991b1b" }}>{ratio(wireTotalSafe, gzTotalSafe)}</b>
                  </div>
                </div>
              </div>

              <div style={{ marginTop: 10, borderRadius: 12, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10, fontSize: 11, color: "#374151", lineHeight: 1.45 }}>
                <div style={{ fontWeight: 900, color: "#111827" }}>Scale projection</div>
                <div style={{ marginTop: 6 }}>
                  <b>1,000 frames:</b>{" "}
                  {proj1k ? (
                    <>
                      WirePack ≈ <b>{fmtKB(proj1k.wire)}</b> vs gzip ≈ <b>{fmtKB(proj1k.gz)}</b>{" "}
                      <span style={{ color: proj1k.pctSmaller >= 0 ? "#065f46" : "#991b1b", fontWeight: 900 }}>
                        ({proj1k.pctSmaller >= 0 ? "-" : "+"}{Math.abs(proj1k.pctSmaller).toFixed(1)}%)
                      </span>
                    </>
                  ) : (
                    "—"
                  )}
                </div>
                <div style={{ marginTop: 6 }}>
                  <b>10,000 frames:</b>{" "}
                  {proj10k ? (
                    <>
                      WirePack ≈ <b>{fmtKB(proj10k.wire)}</b> vs gzip ≈ <b>{fmtKB(proj10k.gz)}</b>{" "}
                      <span style={{ color: proj10k.pctSmaller >= 0 ? "#065f46" : "#991b1b", fontWeight: 900 }}>
                        ({proj10k.pctSmaller >= 0 ? "-" : "+"}{Math.abs(proj10k.pctSmaller).toFixed(1)}%)
                      </span>
                    </>
                  ) : (
                    "—"
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </div>

        {/* RIGHT */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, minHeight: 0 }}>
          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: "#111827", marginBottom: 6 }}>Stats</div>

            {mode === "single" ? (
              <div style={{ fontSize: 11, color: "#4b5563", display: "flex", flexDirection: "column", gap: 6 }}>
                <div>
                  raw: <code>{rawCanonBytes == null ? "—" : `${bytes(rawCanonBytes)} (${rawCanonBytes} B)`}</code>
                </div>
                <div style={{ paddingTop: 6, borderTop: "1px solid #e5e7eb" }}>
                  <div style={{ fontWeight: 800, color: "#111827" }}>WirePack v46</div>
                  <div>
                    template: <code>{tmplBytesOut == null ? "—" : `${bytes(tmplBytesOut)} (${tmplBytesOut} B)`}</code>
                  </div>
                  <div>
                    delta: <code>{deltaBytesOut == null ? "—" : `${bytes(deltaBytesOut)} (${deltaBytesOut} B)`}</code>
                  </div>
                  <div>
                    roundtrip: <code>{wireOk === true ? "OK" : wireOk === false ? "FAIL" : "—"}</code>
                  </div>
                </div>
                <div style={{ paddingTop: 6, borderTop: "1px solid #e5e7eb" }}>
                  <div style={{ fontWeight: 800, color: "#111827" }}>gzip</div>
                  <div>
                    out: <code>{gzipBytesOut == null ? "—" : `${bytes(gzipBytesOut)} (${gzipBytesOut} B)`}</code>
                  </div>
                  <div>
                    roundtrip: <code>{gzipOk === true ? "OK" : gzipOk === false ? "FAIL" : "—"}</code>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 11, color: "#4b5563", display: "flex", flexDirection: "column", gap: 6 }}>
                <div>
                  frames: <code>{framesSent == null || framesPlanned == null ? "—" : `${framesSent}/${framesPlanned}`}</code>{" "}
                  {busy ? <span style={{ color: "#6b7280" }}>(running…)</span> : null}
                </div>

                <div style={{ paddingTop: 6, borderTop: "1px solid #e5e7eb" }}>
                  <div style={{ fontWeight: 800, color: "#111827" }}>WirePack v46</div>
                  <div>
                    template: <code>{wireTemplateBytes == null ? "—" : `${bytes(wireTemplateBytes)} (${wireTemplateBytes} B)`}</code>
                  </div>
                  <div>
                    delta total: <code>{wireDeltaTotalBytes == null ? "—" : `${bytes(wireDeltaTotalBytes)} (${wireDeltaTotalBytes} B)`}</code>
                  </div>
                  <div>
                    avg delta: <code>{wireAvgDeltaBytes == null ? "—" : `${wireAvgDeltaBytes} B`}</code>
                  </div>
                  <div>
                    total: <code>{wireTotalBytes == null ? "—" : `${bytes(wireTotalBytes)} (${wireTotalBytes} B)`}</code>
                  </div>
                  <div>
                    roundtrip(last): <code>{streamRoundtripOk === true ? "OK" : streamRoundtripOk === false ? "FAIL" : "—"}</code>
                  </div>
                </div>

                <div style={{ paddingTop: 6, borderTop: "1px solid #e5e7eb" }}>
                  <div style={{ fontWeight: 800, color: "#111827" }}>gzip baseline</div>
                  <div>
                    total: <code>{gzipTotalBytes == null ? "—" : `${bytes(gzipTotalBytes)} (${gzipTotalBytes} B)`}</code>
                  </div>
                  <div>
                    avg/frame: <code>{gzipAvgBytes == null ? "—" : `${gzipAvgBytes} B`}</code>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10, fontSize: 11, color: "#6b7280" }}>
            Endpoints used:
            <div style={{ marginTop: 6 }}>
              <code>POST /api/wirepack/v46/session/new</code>
            </div>
            <div style={{ marginTop: 6 }}>
              <code>POST /api/wirepack/v46/encode_struct</code>
            </div>
            <div style={{ marginTop: 6 }}>
              <code>POST /api/wirepack/v46/decode_struct</code>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// -------------------------------
// Error boundary (so “white page” becomes a visible error)
// -------------------------------

class DemoErrorBoundary extends React.Component<{ children: React.ReactNode }, { err: any }> {
  state = { err: null as any };
  static getDerivedStateFromError(err: any) {
    return { err };
  }
  componentDidCatch(err: any) {
    // keep in console too
    // eslint-disable-next-line no-console
    console.error("Demo crashed:", err);
  }
  render() {
    if (this.state.err) {
      return (
        <div style={{ borderRadius: 14, border: "1px solid #fecaca", background: "#fff", padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#991b1b" }}>Demo crashed during render</div>
          <pre style={{ marginTop: 8, fontSize: 11, color: "#111827", whiteSpace: "pre-wrap" }}>
            {String(this.state.err?.stack || this.state.err?.message || this.state.err)}
          </pre>
        </div>
      );
    }
    return this.props.children as any;
  }
}

// -------------------------------
// Default export: the shell
// -------------------------------

export default function WirePackDemo() {
  const demos: DemoMeta[] = useMemo(
    () => [
      {
        id: "v46_transport_streaming",
        tab: "transport",
        title: "v46 — Streaming transport",
        blurb: "Template once + deltas (real endpoints) vs gzip-per-frame baseline.",
        Component: TransportV46Demo,
      },
      {
        id: "v44_sql_on_streams",
        tab: "analytics",
        title: "v44 — SQL on streams",
        blurb: "Query-on-stream analytics (existing component).",
        Component: () => <V44SqlOnStreamsDemo />,
      },
      {
        id: "v32_heavy_hitters",
        tab: "analytics",
        title: "v32 — Heavy hitters (Top-K)",
        blurb: "Top-K activity on compressed streams + verifiable receipt.",
        Component: () => <V32HeavyHittersDemo />,
      },
      {
        id: "v29_projection_q",
        tab: "analytics",
        title: "v29 — Projection(Q)",
        blurb: "First query primitive: track only |Q| indices and still match full replay (receipt-locked).",
        Component: () => <V29ProjectionDemo />,
      },
      {
        id: "v10_streaming_transport",
        tab: "transport",
        title: "v10 — Streaming transport",
        blurb: "Template cache + deltas + MTU packet estimate + deterministic receipt (real endpoints).",
        Component: () => <V10StreamingTransportDemo />,
      },
      {
        id: "v45_cross_language_vectors",
        tab: "trust",
        title: "v45 — Cross-language vectors",
        blurb: "Byte-identical template+delta across implementations + stable final hash.",
        Component: () => <V45CrossLanguageVectorsDemo />,
      },
      {
        id: "v30_sum_over_q",
        tab: "analytics",
        title: "v30 — Sum over Q",
        blurb: "Maintain SUM over a query set Q incrementally; matches full replay (receipt-locked).",
        Component: () => <V30SumOverQDemo />,
      },
      {
        id: "v33_range_sums",
        tab: "analytics",
        title: "v33 — Range sums (L..R)",
        blurb: "Interval queries without scanning; streaming range sum is O(log n) (receipt-locked).",
        Component: () => <V33RangeSumsDemo />,
      },
      {
        id: "v41_receipt_gated_queries",
        tab: "trust",
        title: "v41 — Receipt-gated queries",
        blurb: "You can’t query unless the receipt chain verifies (anti demo-theater). Shows lock/unlock + ancestry + drift check.",
        Component: () => <V41ReceiptGatedQueriesDemo />,
      },
      {
        id: "v38_trust_receipts",
        tab: "trust",
        title: "v38 — Trust & receipts",
        blurb: "Canonical bytes + replay invariants + deterministic receipts (real endpoint).",
        Component: () => <V38TrustReceiptsDemo />,
      },
    ],
    [],
  );

  const [tab, setTab] = useState<TabId>("transport");
  const demosForTab = demos.filter((d) => d.tab === tab);

  const [demoId, setDemoId] = useState<DemoId>("v46_transport_streaming");

  useEffect(() => {
    // keep demoId valid when switching tabs
    const allowed = demosForTab.map((d) => d.id);
    if (!allowed.includes(demoId)) setDemoId(demosForTab[0]?.id || "v46_transport_streaming");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const active = demos.find((d) => d.id === demoId) || demos[0];
  const ActiveDemo = active.Component;

  return (
    <div style={{ padding: 14, background: "#f9fafb", minHeight: "100vh" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 900, color: "#111827" }}>WirePack demos</div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>{active.blurb}</div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <TabButton active={tab === "transport"} onClick={() => setTab("transport")}>Transport</TabButton>
          <TabButton active={tab === "analytics"} onClick={() => setTab("analytics")}>Analytics</TabButton>
          <TabButton active={tab === "trust"} onClick={() => setTab("trust")}>Trust</TabButton>

          <select
            value={demoId}
            onChange={(e) => setDemoId(e.target.value as DemoId)}
            style={{ padding: "6px 10px", borderRadius: 999, border: "1px solid #e5e7eb", background: "#fff", fontSize: 11 }}
          >
            {demosForTab.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div style={{ marginTop: 12 }}>
        <DemoErrorBoundary>
          {/* IMPORTANT: render as a component, never call it like a function */}
          <ActiveDemo />
        </DemoErrorBoundary>
      </div>
    </div>
  );
}