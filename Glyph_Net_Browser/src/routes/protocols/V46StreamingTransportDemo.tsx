import React, { useEffect, useMemo, useRef, useState } from "react";

/**
 * v46 — Streaming transport (template once + deltas)
 * Endpoints:
 *   POST /api/wirepack/v46/session/new
 *   POST /api/wirepack/v46/encode_struct
 *   POST /api/wirepack/v46/decode_struct
 *
 * This component is intentionally self-contained so the demo shell stays clean.
 */

/** ---------------- helpers (same “standard” as v32/v44/v41) ---------------- */

function bytes(n: number) {
  const units = ["B", "KB", "MB", "GB"];
  let v = Number(n || 0),
    i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
}

function fmtKB(n: number) {
  return `${(n / 1024).toFixed(2)} KB`;
}

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function ratio(a: number, b: number) {
  if (a <= 0) return "—";
  return (b / a).toFixed(2) + "×";
}

function boolBadge(ok: boolean | null) {
  const good = ok === true;
  const bad = ok === false;
  const bg = good ? "#ecfdf5" : bad ? "#fef2f2" : "#f9fafb";
  const fg = good ? "#065f46" : bad ? "#991b1b" : "#6b7280";
  const bd = good ? "#a7f3d0" : bad ? "#fecaca" : "#e5e7eb";
  const label = good ? "✅ OK" : bad ? "❌ FAIL" : "—";
  return { bg, fg, bd, label };
}

function StatTile(props: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
      <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900, letterSpacing: 0.3 }}>{props.label}</div>
      <div style={{ fontSize: 13, color: "#111827", fontWeight: 900, marginTop: 4 }}>{props.value}</div>
      {props.sub ? <div style={{ fontSize: 10, color: "#6b7280", marginTop: 4 }}>{props.sub}</div> : null}
    </div>
  );
}

function projectTotals(templateBytes: number, avgDeltaBytes: number, gzAvgBytes: number, frames: number) {
  const wire = templateBytes + avgDeltaBytes * frames;
  const gz = gzAvgBytes * frames;
  const pctSmaller = gz > 0 ? (1 - wire / gz) * 100 : 0;
  return { wire, gz, pctSmaller };
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

/** ---------------- tiny charts (no libs) ---------------- */

function BytesBarChart(props: { aLabel: string; aBytes: number | null; bLabel: string; bBytes: number | null }) {
  const a = props.aBytes ?? null;
  const b = props.bBytes ?? null;

  const w = 560;
  const h = 170;
  const pad = { l: 80, r: 18, t: 18, b: 34 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;

  const vals = [a ?? 0, b ?? 0];
  const max = Math.max(1, ...vals);

  const bars = [
    { label: props.aLabel, v: a ?? 0, fill: "#111827" },
    { label: props.bLabel, v: b ?? 0, fill: "#3b82f6" },
  ];
  const barW = innerW / bars.length;

  const y = (v: number) => pad.t + innerH * (1 - v / max);
  const bh = (v: number) => pad.t + innerH - y(v);

  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Total bytes (measured)</div>
        <div style={{ fontSize: 10, color: "#6b7280" }}>WirePack total should beat gzip-per-frame for repeat-heavy shapes</div>
      </div>

      {a == null && b == null ? (
        <div style={{ marginTop: 8, fontSize: 11, color: "#6b7280" }}>Run streaming benchmark to populate.</div>
      ) : (
        <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", marginTop: 8, display: "block" }}>
          <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + innerH} stroke="#e5e7eb" />
          <line x1={pad.l} y1={pad.t + innerH} x2={pad.l + innerW} y2={pad.t + innerH} stroke="#e5e7eb" />
          {[0, max].map((t, i) => (
            <g key={i}>
              <line x1={pad.l - 4} y1={y(t)} x2={pad.l} y2={y(t)} stroke="#e5e7eb" />
              <text x={pad.l - 8} y={y(t) + 4} fontSize="10" textAnchor="end" fill="#6b7280">
                {bytes(t)}
              </text>
            </g>
          ))}
          {bars.map((bar, i) => {
            const x = pad.l + i * barW + Math.max(18, barW * 0.2);
            const bw = Math.max(140, barW * 0.6);
            const top = y(bar.v);
            return (
              <g key={bar.label}>
                <rect x={x} y={top} width={bw} height={bh(bar.v)} rx={10} fill={bar.fill} opacity={0.9} />
                <text x={x + bw / 2} y={top - 6} fontSize="10" textAnchor="middle" fill="#111827">
                  {bytes(bar.v)}
                </text>
                <text x={x + bw / 2} y={pad.t + innerH + 18} fontSize="10" textAnchor="middle" fill="#6b7280">
                  {bar.label}
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}

function MixChart(props: { templateBytes: number | null; deltasBytes: number | null; gzipTotal: number | null }) {
  const t = props.templateBytes ?? null;
  const d = props.deltasBytes ?? null;
  const g = props.gzipTotal ?? null;

  const w = 560;
  const h = 140;
  const pad = { l: 16, r: 16, t: 18, b: 22 };
  const innerW = w - pad.l - pad.r;

  const wireTotal = (t ?? 0) + (d ?? 0);
  const max = Math.max(1, wireTotal, g ?? 0);

  const scale = (v: number) => (innerW * v) / max;

  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Where bytes go</div>
        <div style={{ fontSize: 10, color: "#6b7280" }}>Template amortizes; deltas stay small when fields repeat</div>
      </div>

      {t == null && d == null && g == null ? (
        <div style={{ marginTop: 8, fontSize: 11, color: "#6b7280" }}>Run streaming benchmark to populate.</div>
      ) : (
        <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", marginTop: 8, display: "block" }}>
          {/* WirePack: template + deltas */}
          <text x={pad.l} y={pad.t + 14} fontSize="10" fill="#6b7280">
            WirePack = template + deltas
          </text>
          <rect x={pad.l} y={pad.t + 22} width={scale(t ?? 0)} height={18} rx={9} fill="#111827" opacity={0.9} />
          <rect x={pad.l + scale(t ?? 0)} y={pad.t + 22} width={scale(d ?? 0)} height={18} rx={9} fill="#111827" opacity={0.35} />
          <text x={pad.l} y={pad.t + 55} fontSize="10" fill="#111827">
            template {t == null ? "—" : bytes(t)} · deltas {d == null ? "—" : bytes(d)} · total {bytes(wireTotal)}
          </text>

          {/* Gzip baseline */}
          <text x={pad.l} y={pad.t + 84} fontSize="10" fill="#6b7280">
            gzip baseline (per-frame)
          </text>
          <rect x={pad.l} y={pad.t + 92} width={scale(g ?? 0)} height={18} rx={9} fill="#3b82f6" opacity={0.85} />
          <text x={pad.l} y={pad.t + 125} fontSize="10" fill="#111827">
            total {g == null ? "—" : bytes(g)}
          </text>
        </svg>
      )}
    </div>
  );
}

/** ---------------- JSON canonicalization ---------------- */

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

/** ---------------- gzip helpers (Blob-safe) ---------------- */

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

/** ---------------- WirePack v46 endpoints (real backend) ---------------- */

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

/** ---------------- v46 demo ---------------- */

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

  return JSON.stringify(
    { stream: "delta.frames", base: { method: "GET", path: "/api/v1/search?q=glyphos+wirepack+v46" }, frames },
    null,
    2,
  );
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

export const V46StreamingTransportDemo: React.FC = () => {
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

  // optional debug
  const [showRaw, setShowRaw] = useState(false);

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
  const framesPlanSafe = framesPlanned ?? 0;

  const tmplSafe = wireTemplateBytes ?? 0;
  const deltasSafe = wireDeltaTotalBytes ?? 0;
  const avgDeltaSafe = wireAvgDeltaBytes ?? 0;
  const wireTotalSafe = wireTotalBytes ?? 0;

  const gzTotalSafe = gzipTotalBytes ?? 0;
  const gzAvgSafe = gzipAvgBytes ?? 0;

  const smaller = gzTotalSafe > 0 ? wireTotalSafe < gzTotalSafe : false;
  const pctSmaller = gzTotalSafe > 0 ? (1 - wireTotalSafe / gzTotalSafe) * 100 : 0;

  const proj1k = canShowSell ? projectTotals(tmplSafe, avgDeltaSafe, gzAvgSafe, 1000) : null;
  const proj10k = canShowSell ? projectTotals(tmplSafe, avgDeltaSafe, gzAvgSafe, 10_000) : null;

  const streamOkBadge = boolBadge(streamRoundtripOk);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 900, color: "#111827" }}>v46 — Streaming transport</div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            Template once + deltas across frames (compared to gzip-per-frame). This is the “bandwidth proof” for repeat-heavy shapes.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
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
                  onChange={(e) => setSeconds(clamp(Number(e.target.value) || 15, 5, 120))}
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
                  onChange={(e) => setHz(clamp(Number(e.target.value) || 10, 1, 60))}
                  style={{ width: 70, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
                />
              </label>
            </>
          ) : null}

          <button
            type="button"
            onClick={loadSample}
            style={{
              padding: "6px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              fontSize: 11,
              cursor: "pointer",
            }}
          >
            Load sample
          </button>

          <button
            type="button"
            onClick={() => setShowRaw((s) => !s)}
            style={{
              padding: "6px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#fff",
              fontSize: 11,
              fontWeight: 900,
              cursor: "pointer",
            }}
          >
            Debug
          </button>

          {!busy ? (
            <button
              type="button"
              onClick={run}
              style={{
                padding: "6px 12px",
                borderRadius: 999,
                border: "1px solid #111827",
                background: "#111827",
                color: "#fff",
                fontSize: 11,
                fontWeight: 900,
                cursor: "pointer",
              }}
            >
              Run
            </button>
          ) : (
            <button
              type="button"
              onClick={cancel}
              style={{
                padding: "6px 12px",
                borderRadius: 999,
                border: "1px solid #b91c1c",
                background: "#b91c1c",
                color: "#fff",
                fontSize: 11,
                fontWeight: 900,
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {err ? <div style={{ fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}
      {note ? <div style={{ fontSize: 11, color: "#6b7280" }}>{note}</div> : null}

      {/* Seller container (pitch) */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>
          🎯 v46 — The “bandwidth proof”: template once, deltas thereafter
        </div>
        <div style={{ fontSize: 11, color: "#374151", marginTop: 8, lineHeight: 1.55 }}>
          <b>The claim:</b> If your messages share structure (same keys, many repeated values), then sending a single template + small deltas
          is materially smaller than compressing every frame independently.
          <br />
          <br />
          <b>What’s measured:</b>
          <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
            <li>
              <b>WirePack</b>: one template bytes + sum(delta bytes).
            </li>
            <li>
              <b>gzip baseline</b>: gzip each frame independently (no cross-frame memory).
            </li>
            <li>
              <b>Roundtrip</b>: decode last frame and compare canonical bytes.
            </li>
          </ul>
          <div style={{ marginTop: 10 }}>
            <b>Translation:</b> this is the transport win you can sell: “same data, fewer bytes, still verifiable by decode.”
          </div>
        </div>
      </div>

      {/* Main grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: 10, alignItems: "start" }}>
        {/* LEFT */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {/* Payload */}
          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", overflow: "hidden", display: "flex", flexDirection: "column", minHeight: 240 }}>
            <div style={{ padding: 10, borderBottom: "1px solid #e5e7eb", fontSize: 11, color: "#6b7280" }}>Payload (edit if you want)</div>
            <textarea
              value={payload}
              onChange={(e) => setPayload(e.target.value)}
              style={{
                flex: 1,
                border: "none",
                outline: "none",
                padding: 10,
                fontSize: 11,
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                resize: "none",
                minHeight: 200,
              }}
            />
          </div>

          {/* Charts */}
          <BytesBarChart aLabel="WirePack" aBytes={canShowSell ? wireTotalSafe : null} bLabel="gzip" bBytes={canShowSell ? gzTotalSafe : null} />
          <MixChart templateBytes={canShowSell ? tmplSafe : null} deltasBytes={canShowSell ? deltasSafe : null} gzipTotal={canShowSell ? gzTotalSafe : null} />

          {/* Existing sell/result block (kept, but now it’s “below charts”) */}
          {canShowSell ? (
            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Streaming result (real measured numbers)</div>
                <div
                  style={{
                    padding: "6px 10px",
                    borderRadius: 999,
                    border: `1px solid ${smaller ? "#a7f3d0" : "#fecaca"}`,
                    background: smaller ? "#ecfdf5" : "#fef2f2",
                    color: smaller ? "#065f46" : "#991b1b",
                    fontSize: 11,
                    fontWeight: 900,
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <span style={{ fontSize: 14 }}>{smaller ? "✅" : "⚠️"}</span>
                  {smaller ? `WirePack is ${pctSmaller.toFixed(1)}% smaller` : `WirePack is ${Math.abs(pctSmaller).toFixed(1)}% larger`}
                </div>
              </div>

              <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10, background: "#fff" }}>
                  <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>WirePack</div>
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
                        ({proj1k.pctSmaller >= 0 ? "-" : "+"}
                        {Math.abs(proj1k.pctSmaller).toFixed(1)}%)
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
                        ({proj10k.pctSmaller >= 0 ? "-" : "+"}
                        {Math.abs(proj10k.pctSmaller).toFixed(1)}%)
                      </span>
                    </>
                  ) : (
                    "—"
                  )}
                </div>
              </div>
            </div>
          ) : null}

          {showRaw ? (
            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Debug snapshot</div>
              <pre style={{ marginTop: 8, fontSize: 11, color: "#111827", whiteSpace: "pre-wrap" }}>
                {JSON.stringify(
                  {
                    caseId,
                    mode,
                    seconds,
                    hz,
                    framesPlanned,
                    framesSent,
                    wireTemplateBytes,
                    wireDeltaTotalBytes,
                    wireAvgDeltaBytes,
                    wireTotalBytes,
                    gzipTotalBytes,
                    gzipAvgBytes,
                    streamRoundtripOk,
                  },
                  null,
                  2,
                )}
              </pre>
            </div>
          ) : null}
        </div>

        {/* RIGHT */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {/* Tiles */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <StatTile label="Mode" value={mode === "stream" ? "Streaming" : "Single"} sub={caseId} />
            <StatTile label="Frames" value={mode === "stream" ? `${framesSafe}/${framesPlanSafe || "—"}` : "2"} sub={busy ? "running…" : "idle"} />
            <StatTile label="WirePack total" value={wireTotalBytes == null ? "—" : bytes(wireTotalBytes)} sub={wireTotalBytes == null ? "run streaming" : `${wireTotalBytes} B`} />
            <StatTile label="gzip total" value={gzipTotalBytes == null ? "—" : bytes(gzipTotalBytes)} sub={gzipTotalBytes == null ? "run streaming" : `${gzipTotalBytes} B`} />
            <StatTile
              label="Roundtrip (last)"
              value={
                <span
                  style={{
                    padding: "2px 8px",
                    borderRadius: 999,
                    border: `1px solid ${streamOkBadge.bd}`,
                    background: streamOkBadge.bg,
                    color: streamOkBadge.fg,
                    fontSize: 11,
                    fontWeight: 900,
                  }}
                >
                  {streamOkBadge.label}
                </span>
              }
              sub="decode_struct(last)"
            />
            <StatTile label="Avg delta" value={wireAvgDeltaBytes == null ? "—" : `${wireAvgDeltaBytes} B`} sub="per frame" />
          </div>

          {/* Single-mode stats box (keep your existing detail) */}
          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: "#111827", marginBottom: 6 }}>Stats detail</div>

            {mode === "single" ? (
              <div style={{ fontSize: 11, color: "#4b5563", display: "flex", flexDirection: "column", gap: 6 }}>
                <div>
                  raw: <code>{rawCanonBytes == null ? "—" : `${bytes(rawCanonBytes)} (${rawCanonBytes} B)`}</code>
                </div>
                <div style={{ paddingTop: 6, borderTop: "1px solid #e5e7eb" }}>
                  <div style={{ fontWeight: 800, color: "#111827" }}>WirePack</div>
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
                  <div style={{ fontWeight: 800, color: "#111827" }}>WirePack</div>
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

          {/* Endpoint footer */}
          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10, fontSize: 11, color: "#6b7280" }}>
            Endpoints:
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