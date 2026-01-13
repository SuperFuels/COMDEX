import React, { useMemo, useRef, useState } from "react";

/**
 * v10 — Streaming transport (template once + deltas)
 * Uses real backend endpoints (v46 session-aware codec) to measure bytes + “streaming live”.
 *
 * Endpoints:
 *   POST /api/wirepack/v46/session/new
 *   POST /api/wirepack/v46/encode_struct
 *   POST /api/wirepack/v46/decode_struct   (last frame roundtrip)
 */

// -------------------------------
// tiny helpers (keep self-contained)
// -------------------------------

async function fetchJson(url: string, body: any, timeoutMs = 15000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body ?? {}),
      signal: ctrl.signal,
    });
    const txt = await r.text();
    let json: any = {};
    try {
      json = txt ? JSON.parse(txt) : {};
    } catch {
      json = { _nonJson: true, _text: txt.slice(0, 400) };
    }
    return { ok: r.ok, status: r.status, json };
  } finally {
    clearTimeout(t);
  }
}

function bytes(n: number) {
  const units = ["B", "KB", "MB", "GB"];
  let v = Number(n || 0);
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
}

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function ceilDiv(a: number, b: number) {
  const bb = Number(b || 0);
  if (!Number.isFinite(bb) || bb <= 0) return 0;
  const aa = Number(a || 0);
  return Math.floor((aa + bb - 1) / bb);
}

function tri(ok: boolean | null) {
  if (ok === null) return { label: "—", color: "#6b7280", bg: "#f9fafb", bd: "#e5e7eb", icon: "•" };
  return ok
    ? { label: "OK", color: "#065f46", bg: "#ecfdf5", bd: "#a7f3d0", icon: "✅" }
    : { label: "FAIL", color: "#991b1b", bg: "#fef2f2", bd: "#fecaca", icon: "⚠️" };
}

function Badge(props: { ok: boolean | null; label: string }) {
  const t = tri(props.ok);
  return (
    <span
      style={{
        padding: "5px 10px",
        borderRadius: 999,
        border: `1px solid ${t.bd}`,
        background: t.bg,
        color: t.color,
        fontSize: 11,
        fontWeight: 900,
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        whiteSpace: "nowrap",
      }}
    >
      <span style={{ fontSize: 12 }}>{t.icon}</span>
      {props.label}
    </span>
  );
}

function pillStyle(active: boolean) {
  return {
    padding: "6px 10px",
    borderRadius: 999,
    border: "1px solid " + (active ? "#111827" : "#e5e7eb"),
    background: active ? "#111827" : "#fff",
    color: active ? "#fff" : "#111827",
    fontSize: 11,
    fontWeight: 900 as const,
    cursor: "pointer",
    whiteSpace: "nowrap" as const,
  };
}

function cardStyle() {
  return { borderRadius: 16, border: "1px solid #e5e7eb", background: "#fff", padding: 12 };
}

function miniLabel() {
  return { fontSize: 11, color: "#374151", fontWeight: 900 as const };
}

function miniText() {
  return { fontSize: 11, color: "#6b7280", lineHeight: 1.45 };
}

// Deterministic PRNG (xorshift32)
function rng32(seed: number) {
  let x = (seed >>> 0) || 1;
  return () => {
    x ^= (x << 13) >>> 0;
    x ^= (x >>> 17) >>> 0;
    x ^= (x << 5) >>> 0;
    return x >>> 0;
  };
}

// Canonical JSON stringify (stable field order)
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

async function sha256HexUtf8(s: string): Promise<string> {
  try {
    const u8 = new TextEncoder().encode(s);
    const h = await crypto.subtle.digest("SHA-256", u8);
    const b = new Uint8Array(h);
    return Array.from(b).map((x) => x.toString(16).padStart(2, "0")).join("");
  } catch {
    return "";
  }
}

// gzip (browser CompressionStream) — best effort
async function gzipLenUtf8(s: string): Promise<number | null> {
  try {
    // @ts-ignore
    if (typeof CompressionStream === "undefined") return null;
    const u8 = new TextEncoder().encode(s);
    const copy = new Uint8Array(u8);
    // @ts-ignore
    const stream = new Blob([copy]).stream().pipeThrough(new CompressionStream("gzip"));
    const ab = await new Response(stream).arrayBuffer();
    return new Uint8Array(ab).length;
  } catch {
    return null;
  }
}

// -------------------------------
// “real endpoints” (v46 session codec)
// -------------------------------

async function wpSessionNew() {
  const { ok, status, json } = await fetchJson("/api/wirepack/v46/session/new", {}, 15000);
  if (!ok) throw new Error(`session/new HTTP ${status}: ${JSON.stringify(json)}`);
  const sid = String(json?.session_id || "");
  if (!sid) throw new Error("session/new: missing session_id");
  return sid;
}

async function wpEncodeStruct(session_id: string, json_text: string) {
  const { ok, status, json } = await fetchJson("/api/wirepack/v46/encode_struct", { session_id, json_text }, 20000);
  if (!ok) throw new Error(`encode_struct HTTP ${status}: ${JSON.stringify(json)}`);
  return {
    kind: String(json?.kind || ""), // "template" | "delta"
    bytes_out: Number(json?.bytes_out || 0),
    encoded_b64: String(json?.encoded_b64 || ""),
  };
}

async function wpDecodeStruct(session_id: string, encoded_b64: string) {
  const { ok, status, json } = await fetchJson("/api/wirepack/v46/decode_struct", { session_id, encoded_b64 }, 20000);
  if (!ok) throw new Error(`decode_struct HTTP ${status}: ${JSON.stringify(json)}`);
  return {
    kind: String(json?.kind || ""),
    decoded_text: String(json?.decoded_text || ""),
  };
}

// -------------------------------
// deterministic payload generator (transport-friendly)
// -------------------------------

type CaseId = "http" | "iot" | "sql";

function makeBase(caseId: CaseId) {
  if (caseId === "http") {
    const headers = Array.from({ length: 120 }).map((_, i) => ({
      k: `x-h-${i}`,
      v: `token=${"abc123".repeat(6)}; scope=read:all; region=eu; trace=000`,
    }));
    return {
      stream: "http.frames",
      method: "GET",
      path: "/api/v1/search?q=glyphos+wirepack",
      headers,
      body: null,
    };
  }
  if (caseId === "iot") {
    return {
      stream: "iot.telemetry",
      device: "dev_01",
      readings: Array.from({ length: 64 }).map((_, i) => ({
        t: 1700000000000 + i * 250,
        temp_c: 18.5 + (i % 7) * 0.1,
        hum: 0.45 + (i % 11) * 0.01,
        vib: (i % 5) * 0.02,
        flags: { ok: true, cal: i % 16 === 0 },
      })),
    };
  }
  return {
    stream: "sql.rows",
    table: "payments",
    op: "UPSERT",
    rows: Array.from({ length: 200 }).map((_, i) => ({
      id: i + 1,
      user_id: (i % 37) + 1,
      status: ["PENDING", "PAID", "FAILED"][i % 3],
      amount: (i % 97) * 1.25,
      currency: "EUR",
      region: "EU",
      note: `invoice=${Math.floor(i / 3)}; batch=v10`,
    })),
  };
}

function patchFrame(base: any, caseId: CaseId, i: number, R: () => number) {
  const o = typeof structuredClone === "function" ? structuredClone(base) : JSON.parse(JSON.stringify(base));

  const tr3 = String(i % 1000).padStart(3, "0");
  o.t = 1700000000000 + i * 200;

  o._zz_seq = String(i).padStart(6, "0");
  o._zz_note = `checkpoint=${String(i % 1000).padStart(3, "0")}`;

  if (caseId === "http") {
    if (Array.isArray(o.headers) && o.headers[0]?.v) {
      o.headers[0].v = String(o.headers[0].v).replace(/trace=\d+/g, `trace=${tr3}`);
    }
    o.path = `/api/v1/search?q=glyphos+wirepack&j=${R() % 97}`;
  } else if (caseId === "iot") {
    const k = (R() % Math.max(1, o.readings?.length || 1)) >>> 0;
    if (Array.isArray(o.readings) && o.readings[k]) {
      o.readings[k].temp_c = (o.readings[k].temp_c ?? 18.5) + ((R() % 5) - 2) * 0.01;
      o.readings[k].hum = (o.readings[k].hum ?? 0.45) + ((R() % 5) - 2) * 0.001;
    }
    o.device = `dev_${String((i % 24) + 1).padStart(2, "0")}`;
  } else {
    const idx = (R() % Math.max(1, o.rows?.length || 1)) >>> 0;
    if (Array.isArray(o.rows) && o.rows[idx]) {
      o.rows[idx].status = ["PENDING", "PAID", "FAILED"][(i + (R() % 3)) % 3];
      o.rows[idx].note = `invoice=${Math.floor(idx / 3)}; batch=v10; tr=${tr3}`;
    }
  }

  return o;
}

// -------------------------------
// v10 graph (template burst + delta stream + packetization)
// -------------------------------

function svgTransportGraph(opts: {
  templateBytes: number;
  deltaBytesTotal: number;
  wireTotal: number;
  frames: number;
  packetsEstTotal: number;
  payloadPerPacket: number;
  gzTotal: number | null;
  height?: number;
}) {
  const { templateBytes, deltaBytesTotal, wireTotal, frames, packetsEstTotal, payloadPerPacket, gzTotal, height = 210 } = opts;
  const W = 900;
  const H = height;
  const pad = 18;
  const plotW = W - pad * 2;
  const plotH = H - pad * 2;

  const x0 = pad;
  const y0 = pad;
  const x1 = x0 + plotW;

  const bandH = Math.max(18, Math.round(plotH * 0.18));
  const gap = Math.max(14, Math.round(plotH * 0.10));

  const bytesBandY = y0 + Math.round(plotH * 0.12);
  const pktBandY = bytesBandY + bandH + gap;

  const total = Math.max(1, Number(wireTotal || 0));
  const tFrac = Math.max(0, Math.min(1, Number(templateBytes || 0) / total));
  const dFrac = Math.max(0, Math.min(1, Number(deltaBytesTotal || 0) / total));

  const tW = Math.round(plotW * tFrac);
  const dW = Math.round(plotW * dFrac);

  const framesSafe = Math.max(1, Number(frames || 1));
  const bytesPerFrame = total / framesSafe;

  const perFramePkts = payloadPerPacket > 0 ? bytesPerFrame / payloadPerPacket : 0;
  const pktFrac = Math.max(0, Math.min(1, perFramePkts)); // 0..1 means “fits in ~one packet”
  const pktFillW = Math.round(plotW * pktFrac);

  const gz = gzTotal == null ? null : Math.max(1, Number(gzTotal || 0));
  const ratio = gz ? total / gz : null;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="Streaming transport graph">
      <rect x={0} y={0} width={W} height={H} rx={16} ry={16} fill="#fff" />
      <rect x={x0} y={y0} width={plotW} height={plotH} rx={12} ry={12} fill="transparent" stroke="#e5e7eb" />

      {/* Bytes band */}
      <text x={x0} y={bytesBandY - 6} fontSize={11} fill="#6b7280">
        Wire footprint split: template burst vs delta stream
      </text>
      <rect x={x0} y={bytesBandY} width={plotW} height={bandH} rx={12} ry={12} fill="#f9fafb" stroke="#e5e7eb" />
      <rect x={x0} y={bytesBandY} width={Math.max(2, tW)} height={bandH} rx={12} ry={12} fill="#eef2ff" stroke="#c7d2fe" />
      <rect
        x={x0 + Math.max(2, tW)}
        y={bytesBandY}
        width={Math.max(2, dW)}
        height={bandH}
        rx={12}
        ry={12}
        fill="#ecfeff"
        stroke="#a5f3fc"
      />
      <text x={x0} y={bytesBandY + bandH + 14} fontSize={11} fill="#6b7280">
        template={bytes(templateBytes)} · deltas={bytes(deltaBytesTotal)} · total={bytes(total)}
      </text>
      <text x={x1} y={bytesBandY + bandH + 14} fontSize={11} fill="#6b7280" textAnchor="end">
        {ratio == null ? "gzip baseline: —" : `wire/gzip≈${ratio.toFixed(2)}×`}
      </text>

      {/* Packets band */}
      <text x={x0} y={pktBandY - 6} fontSize={11} fill="#6b7280">
        Packetization pressure: avg bytes/frame vs payload budget
      </text>
      <rect x={x0} y={pktBandY} width={plotW} height={bandH} rx={12} ry={12} fill="#f9fafb" stroke="#e5e7eb" />
      <rect x={x0} y={pktBandY} width={Math.max(2, pktFillW)} height={bandH} rx={12} ry={12} fill="#fef9c3" stroke="#fde68a" />
      <line x1={x1} y1={pktBandY - 10} x2={x1} y2={pktBandY + bandH + 10} stroke="#e5e7eb" />
      <text x={x0} y={pktBandY + bandH + 14} fontSize={11} fill="#6b7280">
        frames={framesSafe} · avg/frame≈{bytesPerFrame.toFixed(1)} B · payload≈{payloadPerPacket} B · packets_est_total≈
        {Number(packetsEstTotal || 0).toLocaleString()}
      </text>
      <text x={x1} y={pktBandY + bandH + 14} fontSize={11} fill="#6b7280" textAnchor="end">
        ~1 pkt/frame
      </text>
    </svg>
  );
}

// -------------------------------
// component
// -------------------------------

export const V10StreamingTransportDemo: React.FC = () => {
  // params
  const [seed, setSeed] = useState(1337);
  const [caseId, setCaseId] = useState<CaseId>("http");
  const [seconds, setSeconds] = useState(12);
  const [hz, setHz] = useState(12);

  // MTU story (transport sell): estimate packets
  const [mtu, setMtu] = useState(1200);
  const [headerOverhead, setHeaderOverhead] = useState(80);

  // UI
  const [showRaw, setShowRaw] = useState(false);

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [out, setOut] = useState<any | null>(null);

  const cancelRef = useRef(false);

  const framesPlanned = useMemo(() => Math.max(2, Math.floor(seconds * hz)), [seconds, hz]);
  const payloadPerPacket = Math.max(1, (mtu | 0) - Math.max(0, headerOverhead | 0));

  function applyPreset(which: "balanced" | "stress" | "tiny") {
    if (which === "balanced") {
      setSeed(1337);
      setCaseId("http");
      setSeconds(12);
      setHz(12);
      setMtu(1200);
      setHeaderOverhead(80);
    } else if (which === "stress") {
      setSeed(9001);
      setCaseId("sql");
      setSeconds(20);
      setHz(20);
      setMtu(1200);
      setHeaderOverhead(90);
    } else {
      setSeed(42);
      setCaseId("iot");
      setSeconds(8);
      setHz(10);
      setMtu(800);
      setHeaderOverhead(80);
    }
  }

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setNote(null);
    setOut(null);
    cancelRef.current = false;

    try {
      const R = rng32(seed);
      const base = makeBase(caseId);
      const sid = await wpSessionNew();

      let templateBytes = 0;
      let deltaBytesTotal = 0;
      let templatesCount = 0;

      let gzipTotal = 0;
      let gzipKnown = true;

      let packetsEstTotal = 0;
      let lastEncodedB64 = "";
      let lastCanon = "";

      for (let i = 0; i < framesPlanned; i++) {
        if (cancelRef.current) break;

        const frameObj = patchFrame(base, caseId, i, R);
        const canon = stableStringify(frameObj);
        lastCanon = canon;

        const gzLen = await gzipLenUtf8(canon);
        if (gzLen == null) gzipKnown = false;
        else gzipTotal += gzLen;

        const enc = await wpEncodeStruct(sid, canon);
        lastEncodedB64 = enc.encoded_b64;

        if (enc.kind === "template") {
          templatesCount += 1;
          templateBytes += enc.bytes_out;
        } else {
          deltaBytesTotal += enc.bytes_out;
        }

        packetsEstTotal += ceilDiv(enc.bytes_out, payloadPerPacket);

        if (i % 10 === 0 && i > 0) {
          setNote(`streaming… ${i}/${framesPlanned} frames`);
          setOut((prev: any) => ({
            ...(prev || {}),
            _progress: { framesSent: i, framesPlanned },
            bytes: {
              template_bytes: templateBytes,
              delta_bytes_total: deltaBytesTotal,
              wire_total_bytes: templateBytes + deltaBytesTotal,
              gzip_total_bytes: gzipKnown ? gzipTotal : null,
              packets_est_total: packetsEstTotal,
              mtu,
              header_overhead: headerOverhead,
              payload_per_packet: payloadPerPacket,
            },
          }));
        }
      }

      let roundtrip_ok: boolean | null = null;
      if (lastEncodedB64) {
        try {
          const dec = await wpDecodeStruct(sid, lastEncodedB64);
          roundtrip_ok = dec.decoded_text === lastCanon;
        } catch {
          roundtrip_ok = null;
        }
      }

      const template_once_ok = templatesCount === 1;
      const wire_total_bytes = templateBytes + deltaBytesTotal;

      const receiptCore = {
        demo: "v10",
        claim: "Template once + deltas enables low-bandwidth streaming transport with stable receipts.",
        params: { seed, caseId, seconds, hz, frames: framesPlanned, mtu, headerOverhead },
        bytes: {
          template_bytes: templateBytes,
          delta_bytes_total: deltaBytesTotal,
          wire_total_bytes,
          gzip_total_bytes: gzipKnown ? gzipTotal : null,
          packets_est_total: packetsEstTotal,
          payload_per_packet: payloadPerPacket,
        },
        invariants: { template_once_ok, roundtrip_ok },
      };

      const drift_sha256 = await sha256HexUtf8(stableStringify(receiptCore));
      const LEAN_OK = template_once_ok && roundtrip_ok === true ? 1 : 0;

      setOut({
        ...receiptCore,
        receipts: { drift_sha256, LEAN_OK },
        _progress: { framesSent: framesPlanned, framesPlanned },
      });

      setNote(null);
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

  // parse outputs
  const inv = out?.invariants || {};
  const b = out?.bytes || {};
  const r = out?.receipts || {};
  const prog = out?._progress || null;

  const templateOnceOk = inv?.template_once_ok == null ? null : Boolean(inv.template_once_ok);
  const roundtripOk = inv?.roundtrip_ok == null ? null : Boolean(inv.roundtrip_ok);
  const leanOkVal = r?.LEAN_OK;
  const leanOk = leanOkVal == null ? null : Boolean(Number(leanOkVal));

  const templateBytes = Number(b?.template_bytes ?? 0);
  const deltaBytesTotal = Number(b?.delta_bytes_total ?? 0);
  const wireTotal = Number(b?.wire_total_bytes ?? (templateBytes + deltaBytesTotal));
  const gzTotal = b?.gzip_total_bytes == null ? null : Number(b.gzip_total_bytes || 0);
  const packetsEstTotal = Number(b?.packets_est_total ?? 0);

  const avgPerFrame = framesPlanned > 0 ? wireTotal / framesPlanned : 0;
  const pctSmaller = gzTotal && gzTotal > 0 ? (1 - wireTotal / gzTotal) * 100 : null;

  const minimalCurl = useMemo(() => {
    // v10 is session-based; this is the smallest “prove template+encode works” command set.
    const canon0 = stableStringify(makeBase(caseId));
    return `# 1) create session
SID=$(curl -sS -X POST http://127.0.0.1:8787/api/wirepack/v46/session/new -H 'content-type: application/json' -d '{}' | jq -r .session_id)

# 2) encode one frame (will typically emit template on first call)
curl -sS -X POST http://127.0.0.1:8787/api/wirepack/v46/encode_struct \\
  -H 'content-type: application/json' \\
  -d $(jq -n --arg session_id "$SID" --arg json_text '${canon0.replace(/'/g, "'\\''")}' '{session_id:$session_id,json_text:$json_text}') | jq`;
  }, [caseId]);

  async function copyText(s: string) {
    try {
      await navigator.clipboard.writeText(s);
    } catch {
      // ignore
    }
  }

  return (
    <div style={{ ...cardStyle(), padding: 14 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 900, color: "#111827" }}>
            v10 — Streaming transport <span style={{ fontSize: 11, fontWeight: 900, color: "#6b7280" }}>· template cache + deltas</span>
          </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 3, maxWidth: 860 }}>
            Real endpoint streaming: template once, then tiny deltas per frame — with MTU packet estimate and a deterministic receipt hash.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <Badge ok={templateOnceOk} label={`template_once_ok: ${templateOnceOk === true ? "OK" : templateOnceOk === false ? "FAIL" : "—"}`} />
          <Badge ok={roundtripOk} label={`roundtrip_ok: ${roundtripOk === true ? "OK" : roundtripOk === false ? "FAIL" : "—"}`} />
          <Badge ok={leanOk} label={`LEAN: ${leanOk === true ? "OK" : leanOk === false ? "FAIL" : "—"}`} />

          {!busy ? (
            <button
              type="button"
              onClick={run}
              style={{
                padding: "7px 12px",
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
                padding: "7px 12px",
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

      {/* Presets + quick actions */}
      <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontSize: 11, color: "#6b7280", fontWeight: 900 }}>Presets</span>
        <button type="button" onClick={() => applyPreset("balanced")} style={pillStyle(false)}>
          Balanced
        </button>
        <button type="button" onClick={() => applyPreset("stress")} style={pillStyle(false)}>
          Stress
        </button>
        <button type="button" onClick={() => applyPreset("tiny")} style={pillStyle(false)}>
          Tiny
        </button>

        <span style={{ width: 1, height: 18, background: "#e5e7eb", marginLeft: 6, marginRight: 6 }} />

        <button type="button" onClick={() => copyText(minimalCurl)} style={pillStyle(false)} title="Copy minimal curl">
          Copy curl
        </button>

        <label style={{ display: "inline-flex", gap: 8, alignItems: "center", fontSize: 11, fontWeight: 900, color: "#111827" }}>
          <input type="checkbox" checked={showRaw} onChange={(e) => setShowRaw(e.target.checked)} />
          Raw JSON
        </label>
      </div>

      {err ? <div style={{ marginTop: 10, fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}
      {note ? <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>{note}</div> : null}

      {/* 3-column layout */}
      <div
        style={{
          marginTop: 12,
          display: "grid",
          gridTemplateColumns: "minmax(260px, 320px) minmax(420px, 1fr) minmax(260px, 340px)",
          gap: 12,
        }}
      >
        {/* Left: seller-style narrative panel (NO fake seller fields) */}
        <div style={{ ...cardStyle() }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>🎯 v10 — Transport unlock</div>
            <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900 }}>template once + deltas</div>
          </div>

          <div style={{ marginTop: 8, ...miniText() }}>
            <b>The claim:</b> most streams repeat structure; only a few fields change per frame. Ship <b>template once</b>, then <b>tiny deltas</b>,
            with a deterministic receipt (<code>drift_sha256</code>) and a real network story (<code>packets_est_total</code> under MTU).
          </div>

          <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.55 }}>
            <div>
              <b>This run shape:</b> case=<b>{caseId}</b>, frames=<b>{framesPlanned.toLocaleString()}</b>, MTU=<b>{mtu}</b>, overhead=<b>{headerOverhead}</b>
              {" "}→ payload≈<b>{payloadPerPacket}</b> B
            </div>

            <div style={{ marginTop: 10, borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>Outputs you can pin (this run)</div>
              <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr", gap: 6 }}>
                <div>
                  template_bytes: <b style={{ color: "#111827" }}>{bytes(templateBytes)}</b>
                </div>
                <div>
                  delta_bytes_total: <b style={{ color: "#111827" }}>{bytes(deltaBytesTotal)}</b>
                </div>
                <div>
                  wire_total_bytes: <b style={{ color: "#111827" }}>{bytes(wireTotal)}</b>{" "}
                  <span style={{ color: "#6b7280" }}>({avgPerFrame ? `${avgPerFrame.toFixed(1)} B/frame` : "—"})</span>
                </div>
                <div>
                  packets_est_total: <b style={{ color: "#111827" }}>{packetsEstTotal.toLocaleString()}</b>{" "}
                  <span style={{ color: "#6b7280" }}>(payload≈{payloadPerPacket} B)</span>
                </div>
                <div style={{ color: "#6b7280" }}>
                  drift_sha256: <code>{String(r?.drift_sha256 || "—")}</code>
                </div>
              </div>
            </div>

            <div style={{ marginTop: 10 }}>
              <b>Interpretation:</b> you pay the template burst once, then the stream becomes packet-friendly deltas. That’s the operational win.
            </div>
          </div>

          <div style={{ marginTop: 10, borderTop: "1px solid #f3f4f6", paddingTop: 10 }}>
            <div style={{ ...miniLabel() }}>Endpoints</div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              <div>
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

        {/* Middle: controls + graph + key metrics */}
        <div style={{ ...cardStyle() }}>
          {/* Controls */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(0, 1fr))", gap: 8 }}>
            <label style={{ fontSize: 11, color: "#374151" }}>
              case
              <select
                value={caseId}
                onChange={(e) => setCaseId(e.target.value as any)}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb", background: "#fff" }}
              >
                <option value="http">HTTP-ish</option>
                <option value="iot">IoT</option>
                <option value="sql">SQL-ish</option>
              </select>
            </label>

            <label style={{ fontSize: 11, color: "#374151" }}>
              seed
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value) || 0)}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>

            <label style={{ fontSize: 11, color: "#374151" }}>
              sec
              <input
                type="number"
                value={seconds}
                min={5}
                max={120}
                onChange={(e) => setSeconds(clamp(Number(e.target.value) || 12, 5, 120))}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>

            <label style={{ fontSize: 11, color: "#374151" }}>
              Hz
              <input
                type="number"
                value={hz}
                min={1}
                max={60}
                onChange={(e) => setHz(clamp(Number(e.target.value) || 12, 1, 60))}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>

            <label style={{ fontSize: 11, color: "#374151" }}>
              MTU
              <input
                type="number"
                value={mtu}
                min={128}
                max={9000}
                onChange={(e) => setMtu(clamp(Number(e.target.value) || 1200, 128, 9000))}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>

            <label style={{ fontSize: 11, color: "#374151" }}>
              overhead
              <input
                type="number"
                value={headerOverhead}
                min={0}
                max={512}
                onChange={(e) => setHeaderOverhead(clamp(Number(e.target.value) || 80, 0, 512))}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>
          </div>

          {/* Graph */}
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Streaming transport graph</div>
              <div style={{ fontSize: 11, color: "#374151" }}>
                template_once_ok: <b style={{ color: tri(templateOnceOk).color }}>{tri(templateOnceOk).label}</b>
                {"  "}· roundtrip_ok: <b style={{ color: tri(roundtripOk).color }}>{tri(roundtripOk).label}</b>
                {"  "}· LEAN: <b style={{ color: tri(leanOk).color }}>{tri(leanOk).label}</b>
              </div>
            </div>

            <div style={{ marginTop: 10 }}>
              {out ? (
                <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", overflow: "hidden" }}>
                  {svgTransportGraph({
                    templateBytes,
                    deltaBytesTotal,
                    wireTotal,
                    frames: framesPlanned,
                    packetsEstTotal,
                    payloadPerPacket,
                    gzTotal,
                    height: 210,
                  })}
                </div>
              ) : (
                <div style={{ borderRadius: 16, border: "1px dashed #e5e7eb", background: "#f9fafb", padding: 14, fontSize: 11, color: "#6b7280" }}>
                  No output yet — hit <b>Run</b>.
                </div>
              )}
            </div>

            <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                <div style={{ ...miniLabel() }}>Frames</div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                  planned: <b style={{ color: "#111827" }}>{framesPlanned.toLocaleString()}</b>{" "}
                  {prog ? <span style={{ color: "#6b7280" }}>· sent {String(prog.framesSent)}/{String(prog.framesPlanned)}</span> : null}
                </div>
              </div>

              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                <div style={{ ...miniLabel() }}>Avg / frame</div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                  <b style={{ color: "#111827" }}>{avgPerFrame ? `${avgPerFrame.toFixed(1)} B` : "—"}</b>{" "}
                  <span style={{ color: "#6b7280" }}>(payload≈{payloadPerPacket} B)</span>
                </div>
              </div>

              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                <div style={{ ...miniLabel() }}>Gzip baseline</div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                  <b style={{ color: "#111827" }}>{gzTotal == null ? "—" : bytes(gzTotal)}</b>{" "}
                  {pctSmaller != null ? (
                    <span style={{ color: pctSmaller >= 0 ? "#065f46" : "#991b1b", fontWeight: 900 }}>
                      ({pctSmaller >= 0 ? "-" : "+"}
                      {Math.abs(pctSmaller).toFixed(1)}%)
                    </span>
                  ) : (
                    <span style={{ color: "#6b7280" }}>(unsupported)</span>
                  )}
                </div>
              </div>
            </div>

            <div style={{ marginTop: 10, fontSize: 10, color: "#6b7280" }}>
              Top band: one-time template burst vs ongoing deltas. Bottom band: how close avg frame size is to your MTU payload budget.
            </div>
          </div>

          {/* Output cards */}
          {out ? (
            <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: "#111827", display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                  Invariants
                  <Badge ok={templateOnceOk} label={`template_once_ok: ${templateOnceOk === true ? "OK" : templateOnceOk === false ? "FAIL" : "—"}`} />
                  <Badge ok={roundtripOk} label={`roundtrip_ok: ${roundtripOk === true ? "OK" : roundtripOk === false ? "FAIL" : "—"}`} />
                </div>

                <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
                  <div>
                    template_once_ok: <code>{String(inv.template_once_ok)}</code>
                  </div>
                  <div>
                    roundtrip_ok: <code>{String(inv.roundtrip_ok)}</code>
                  </div>
                </div>
              </div>

              <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: "#111827", display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                  Receipt
                  <Badge ok={leanOk} label={`LEAN_OK: ${leanOk === true ? "OK" : leanOk === false ? "FAIL" : "—"}`} />
                </div>

                <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
                  <div style={{ color: "#6b7280" }}>
                    drift_sha256: <code>{String(r?.drift_sha256 || "—")}</code>
                  </div>

                  <div style={{ marginTop: 10, fontWeight: 900, color: "#111827" }}>Bytes</div>
                  <div>
                    template_bytes: <b style={{ color: "#111827" }}>{bytes(templateBytes)}</b>{" "}
                    <span style={{ color: "#6b7280" }}>{b?.template_bytes != null ? `(${b.template_bytes} B)` : ""}</span>
                  </div>
                  <div>
                    delta_bytes_total: <b style={{ color: "#111827" }}>{bytes(deltaBytesTotal)}</b>{" "}
                    <span style={{ color: "#6b7280" }}>{b?.delta_bytes_total != null ? `(${b.delta_bytes_total} B)` : ""}</span>
                  </div>
                  <div>
                    wire_total_bytes: <b style={{ color: "#111827" }}>{bytes(wireTotal)}</b>{" "}
                    <span style={{ color: "#6b7280" }}>{b?.wire_total_bytes != null ? `(${b.wire_total_bytes} B)` : ""}</span>
                  </div>
                  <div style={{ color: "#6b7280" }}>
                    packets_est_total: <code>{String(b?.packets_est_total ?? "—")}</code>{" "}
                    <span style={{ color: "#6b7280" }}>(payload≈{String(b?.payload_per_packet ?? payloadPerPacket)} B)</span>
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {out && showRaw ? (
            <div style={{ marginTop: 12, borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Raw response</div>
              <pre style={{ marginTop: 8, fontSize: 11, color: "#111827", whiteSpace: "pre-wrap" }}>{JSON.stringify(out, null, 2)}</pre>
            </div>
          ) : null}
        </div>

        {/* Right: compact “why it matters” + minimal curl */}
        <div style={{ ...cardStyle() }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>What’s so special?</div>
            <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900 }}>why v10 matters</div>
          </div>

          <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>1) Template amortization</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                The first frame pays schema cost. After that, frames are deltas. That’s how you get predictable transport at higher Hz.
              </div>
            </div>

            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>2) Network realism (MTU)</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                Packetization drives latency/loss. <code>packets_est_total</code> makes the MTU story concrete instead of “bytes only”.
              </div>
            </div>

            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>3) Receipt-locked streaming</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                <code>drift_sha256</code> fingerprints params + bytes + invariants. Change transport behavior → receipt changes.
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                <code>LEAN_OK</code> is the end-to-end “green”.
              </div>
            </div>

            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
              <div style={{ ...miniLabel() }}>Minimal reproducible curl</div>
              <pre style={{ marginTop: 8, fontSize: 10, color: "#111827", whiteSpace: "pre-wrap" }}>{minimalCurl}</pre>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          marginTop: 12,
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#f9fafb",
          padding: 10,
          fontSize: 11,
          color: "#6b7280",
          display: "flex",
          justifyContent: "space-between",
          gap: 10,
          flexWrap: "wrap",
        }}
      >
        <div>
          endpoints: <code>v46 session codec</code>
        </div>
        <div>
          wire: <b style={{ color: "#111827" }}>{bytes(wireTotal)}</b>{" "}
          <span style={{ color: "#6b7280" }}>
            · frames {framesPlanned.toLocaleString()} · avg/frame {avgPerFrame ? `${avgPerFrame.toFixed(1)} B` : "—"} · payload≈{payloadPerPacket} B
          </span>
        </div>
      </div>
    </div>
  );
};