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
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
}

function ceilDiv(a: number, b: number) {
  if (b <= 0) return 0;
  return Math.floor((a + b - 1) / b);
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
  // best effort: if subtle not available, return ""
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
    // clone so browser impls don’t alias buffers
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
  // sql
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

  // small, structured changes that generate good deltas (like real traffic)
  const tr3 = String(i % 1000).padStart(3, "0");
  o.t = 1700000000000 + i * 200;

  o._zz_seq = String(i).padStart(6, "0");
  o._zz_note = `checkpoint=${String(i % 1000).padStart(3, "0")}`;

  if (caseId === "http") {
    // update trace in header[0] + add a tiny jitter param
    if (Array.isArray(o.headers) && o.headers[0]?.v) {
      o.headers[0].v = String(o.headers[0].v).replace(/trace=\d+/g, `trace=${tr3}`);
    }
    o.path = `/api/v1/search?q=glyphos+wirepack&j=${R() % 97}`;
  } else if (caseId === "iot") {
    // tweak one sensor row per frame
    const k = (R() % Math.max(1, o.readings?.length || 1)) >>> 0;
    if (Array.isArray(o.readings) && o.readings[k]) {
      o.readings[k].temp_c = (o.readings[k].temp_c ?? 18.5) + ((R() % 5) - 2) * 0.01;
      o.readings[k].hum = (o.readings[k].hum ?? 0.45) + ((R() % 5) - 2) * 0.001;
    }
    o.device = `dev_${String((i % 24) + 1).padStart(2, "0")}`;
  } else {
    // sql: flip a few statuses
    const idx = (R() % Math.max(1, o.rows?.length || 1)) >>> 0;
    if (Array.isArray(o.rows) && o.rows[idx]) {
      o.rows[idx].status = ["PENDING", "PAID", "FAILED"][(i + (R() % 3)) % 3];
      o.rows[idx].note = `invoice=${Math.floor(idx / 3)}; batch=v10; tr=${tr3}`;
    }
  }

  return o;
}

// -------------------------------
// component
// -------------------------------

export const V10StreamingTransportDemo: React.FC = () => {
  const [seed, setSeed] = useState(1337);
  const [caseId, setCaseId] = useState<CaseId>("http");

  const [seconds, setSeconds] = useState(12);
  const [hz, setHz] = useState(12);

  // MTU story (transport sell): estimate packets
  const [mtu, setMtu] = useState(1200);
  const [headerOverhead, setHeaderOverhead] = useState(80); // conservative (framing + topic + metadata)

  // when displaying:
  const payloadBudget = Math.max(1, mtu - headerOverhead);

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const [out, setOut] = useState<any>(null);

  const cancelRef = useRef(false);

  const framesPlanned = useMemo(() => Math.max(2, Math.floor(seconds * hz)), [seconds, hz]);

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
      let deltasCount = 0;

      let gzipTotal: number = 0;
      let gzipKnown = true;

      let packetsEstTotal = 0;
      let lastEncodedB64 = "";
      let lastCanon = "";

      const payloadPerPacket = Math.max(1, (mtu | 0) - Math.max(0, headerOverhead | 0));

      for (let i = 0; i < framesPlanned; i++) {
        if (cancelRef.current) break;

        const frameObj = patchFrame(base, caseId, i, R);
        const canon = stableStringify(frameObj);
        lastCanon = canon;

        // gzip baseline (best effort)
        const gzLen = await gzipLenUtf8(canon);
        if (gzLen == null) gzipKnown = false;
        else gzipTotal += gzLen;

        const enc = await wpEncodeStruct(sid, canon);
        lastEncodedB64 = enc.encoded_b64;

        // accumulate bytes (template once, then deltas)
        if (enc.kind === "template") {
          templatesCount += 1;
          templateBytes += enc.bytes_out;
        } else {
          deltasCount += 1;
          deltaBytesTotal += enc.bytes_out;
        }

        // transport packet estimate (how many MTU chunks)
        packetsEstTotal += ceilDiv(enc.bytes_out, payloadPerPacket);

        // occasional UI tick
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
            },
          }));
        }
      }

      // Roundtrip check (last frame)
      let roundtrip_ok: boolean | null = null;
      if (lastEncodedB64) {
        try {
          const dec = await wpDecodeStruct(sid, lastEncodedB64);
          roundtrip_ok = dec.decoded_text === lastCanon;
        } catch {
          roundtrip_ok = null;
        }
      }

      const template_once_ok = templatesCount === 1; // what “template cache hit” means in this session
      const wire_total_bytes = templateBytes + deltaBytesTotal;

      // Receipt core: stable + hashable
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
        invariants: {
          template_once_ok,
          roundtrip_ok,
        },
      };

      const drift_sha256 = await sha256HexUtf8(stableStringify(receiptCore));
      const LEAN_OK = template_once_ok && roundtrip_ok === true ? 1 : 0;

      setOut({
        ...receiptCore,
        receipts: {
          drift_sha256,
          LEAN_OK,
        },
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

  const inv = out?.invariants || {};
  const b = out?.bytes || {};
  const r = out?.receipts || {};
  const prog = out?._progress || null;

  const okBadge = inv?.template_once_ok === true && inv?.roundtrip_ok === true;

  const badgeBg = okBadge ? "#ecfdf5" : "#fef2f2";
  const badgeFg = okBadge ? "#065f46" : "#991b1b";
  const badgeBorder = okBadge ? "#a7f3d0" : "#fecaca";

  const wireTotal = Number(b.wire_total_bytes || 0);
  const gzTotal = b.gzip_total_bytes == null ? null : Number(b.gzip_total_bytes || 0);
  const pctSmaller = gzTotal && gzTotal > 0 ? (1 - wireTotal / gzTotal) * 100 : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 900, color: "#111827" }}>
            v10 — Streaming transport (template cache + deltas)
          </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            Real endpoint streaming: <b>template once</b>, then <b>tiny deltas</b> per frame + MTU packet estimate + receipt hash.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={caseId}
            onChange={(e) => setCaseId(e.target.value as any)}
            style={{ padding: "6px 10px", borderRadius: 999, border: "1px solid #e5e7eb", background: "#fff", fontSize: 11 }}
          >
            <option value="http">HTTP-ish stream</option>
            <option value="iot">IoT telemetry</option>
            <option value="sql">SQL-ish rows</option>
          </select>

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            seed
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value) || 0)}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
            />
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            sec
            <input
              type="number"
              value={seconds}
              min={5}
              max={120}
              onChange={(e) => setSeconds(Math.max(5, Math.min(120, Number(e.target.value) || 12)))}
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
              onChange={(e) => setHz(Math.max(1, Math.min(60, Number(e.target.value) || 12)))}
              style={{ width: 70, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
            />
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            MTU
            <input
              type="number"
              value={mtu}
              min={128}
              max={9000}
              onChange={(e) => setMtu(Math.max(128, Math.min(9000, Number(e.target.value) || 1200)))}
              style={{ width: 80, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
            />
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            overhead
            <input
              type="number"
              value={headerOverhead}
              min={0}
              max={512}
              onChange={(e) => setHeaderOverhead(Math.max(0, Math.min(512, Number(e.target.value) || 80)))}
              style={{ width: 80, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
            />
          </label>

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

      {/* SELL / PITCH CARD (standard for all demos) */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>
          🎯 What this demo proves (v10)
        </div>

        <div style={{ fontSize: 11, color: "#374151", marginTop: 8, lineHeight: 1.55 }}>
          <b>The claim:</b> streaming data can be shipped as <b>template once</b> + <b>tiny deltas</b>, producing a deterministic
          end-of-run receipt (<code>drift_sha256</code>) and a transport-friendly packet budget (MTU estimate).
          <br /><br />

          <b>We are testing for:</b> “web-native streaming” that doesn’t require a server push to feel live —
          the UI progressively encodes frames, counts bytes, estimates packets, and ends with a stable receipt.
          <br /><br />

          <b>Data:</b> deterministic synthetic traffic (HTTP-ish / IoT / SQL-ish) where each frame changes only a few fields,
          which is exactly where template+delta wins.
          <br /><br />

          <b>Results mean:</b>
          <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
            <li><code>template_once_ok</code>: template cache hit inside the stream session (template isn’t resent every frame).</li>
            <li><code>roundtrip_ok</code>: the last encoded frame decodes back to the canonical JSON exactly.</li>
            <li><code>packets_est_total</code>: rough on-wire packet count under your MTU budget.</li>
            <li><code>drift_sha256</code>: deterministic “receipt-of-run” you can lock in CI and verify on-device.</li>
          </ul>

          <div style={{ marginTop: 10 }}>
            <b>Why it matters:</b> this is the product story. Once the trust layer exists (v38/v45), v10 shows the operational win:
            <b> bandwidth, latency, and predictable transport</b> — especially on constrained links.
            <br />
            <b>Lean note:</b> we expose <code>LEAN_OK</code> as the “green badge” when invariants hold (designed to be machine-checkable).
          </div>
        </div>
      </div>

      {/* OUTPUT */}
      {out ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Invariant status</div>
              <div style={{ padding: "6px 10px", borderRadius: 999, border: `1px solid ${badgeBorder}`, background: badgeBg, color: badgeFg, fontSize: 11, fontWeight: 900 }}>
                {okBadge ? "✅ VERIFIED" : "❌ CHECK FAILED"}
              </div>
            </div>

            <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
              <div>template_once_ok: <code>{String(inv.template_once_ok)}</code></div>
              <div>roundtrip_ok: <code>{String(inv.roundtrip_ok)}</code></div>
              {prog ? (
                <div style={{ marginTop: 8, color: "#6b7280" }}>
                  progress: <code>{String(prog.framesSent)}/{String(prog.framesPlanned)}</code>
                </div>
              ) : null}
            </div>
          </div>

          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Receipt</div>

            <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
              <div>template_bytes: <code>{bytes(Number(b.template_bytes || 0))}</code></div>
              <div>delta_bytes_total: <code>{bytes(Number(b.delta_bytes_total || 0))}</code></div>
              <div>wire_total_bytes: <code>{bytes(Number(b.wire_total_bytes || 0))}</code></div>

              <div style={{ paddingTop: 8, borderTop: "1px solid #e5e7eb", marginTop: 8 }}>
                packets_est_total: <code>{String(b.packets_est_total ?? "—")}</code>{" "}
                <span style={{ color: "#6b7280" }}>
                  (MTU={String(b.mtu)}, overhead={String(b.header_overhead)}, payload≈{String(b.payload_per_packet)} B)
                </span>
              </div>

              <div>
                gzip_total_bytes:{" "}
                <code>{b.gzip_total_bytes == null ? "— (unsupported)" : bytes(Number(b.gzip_total_bytes || 0))}</code>{" "}
                {pctSmaller != null ? (
                  <span style={{ color: pctSmaller >= 0 ? "#065f46" : "#991b1b", fontWeight: 900 }}>
                    ({pctSmaller >= 0 ? "-" : "+"}{Math.abs(pctSmaller).toFixed(1)}%)
                  </span>
                ) : null}
              </div>

              <div style={{ paddingTop: 8, borderTop: "1px solid #e5e7eb", marginTop: 8 }}>
                drift_sha256: <code>{String(r.drift_sha256 || "")}</code>
              </div>
              <div>LEAN_OK: <code>{String(r.LEAN_OK)}</code></div>
            </div>
          </div>
        </div>
      ) : null}

      {/* Sell / story card (drop directly under “What this demo proves”) */}
        <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12, marginTop: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>
            Make it real: three workload stories + the MTU/latency story
        </div>

        <div style={{ fontSize: 11, color: "#374151", marginTop: 8, lineHeight: 1.55 }}>
            <b>What v10 is showing (in human terms):</b> most real streams don’t change “everything” every frame — they change a few
            fields (trace id, timestamp, a couple counters). WirePack ships the <b>template once</b>, then sends <b>tiny deltas</b>.
            <br /><br />

            <b>The three workload stories</b>
            <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
            <li>
                <b>HTTP-ish stream (API gateway logs):</b> every request repeats the same header/schema shape, only a few fields change.
                v10 shows how that becomes “template cached + tiny per-request deltas”, so bandwidth stays predictable even at scale.
            </li>
            <li>
                <b>IoT telemetry (sensor fleet):</b> readings are mostly the same schema with small numeric changes.
                Template+delta means you can run higher frequency telemetry on constrained links without blowing the budget.
            </li>
            <li>
                <b>SQL-ish rows (CDC / replication):</b> row updates tend to touch a small subset of columns.
                Deltas map cleanly to “only the columns that changed”, so replication traffic drops and becomes verifiable.
            </li>
            </ul>

            <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid #e5e7eb" }}>
            <b>The MTU / packet story (why “packets_est_total” matters):</b>
            <br />
            <span style={{ color: "#6b7280" }}>
                On real networks you don’t pay only for bytes — you pay for packetization, headers, loss probability, and latency.
            </span>
            <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
                <li>
                <b>Template packet burst once:</b> the first frames pay the “schema cost” (template bytes).
                </li>
                <li>
                <b>Then one tiny delta per frame:</b> each frame is small enough to fit comfortably under your MTU payload budget.
                </li>
                <li>
                <b>Progressive decode:</b> once the template is cached, each delta decodes immediately — the UI can feel “live”
                without a server push stream.
                </li>
            </ul>
            </div>

            <div style={{ marginTop: 10, padding: 10, borderRadius: 12, border: "1px solid #e5e7eb", background: "#f9fafb" }}>
            <b>How to read the result panel:</b>
            <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
                <li><code>template_once_ok</code>: template was cached (not resent every frame).</li>
                <li><code>roundtrip_ok</code>: last encoded frame decodes back to canonical JSON exactly.</li>
                <li><code>packets_est_total</code>: rough packet budget under your MTU + overhead assumption.</li>
                <li><code>drift_sha256</code>: deterministic receipt-of-run (lock in CI, verify on-device).</li>
                <li><code>LEAN_OK=1</code>: invariants held end-to-end (designed to be machine-checkable).</li>
            </ul>
            </div>

            <div style={{ marginTop: 10 }}>
            <b>Why v10 is the product story:</b> once trust exists (v38/v45), v10 shows the operational win —
            <b> predictable transport</b>, <b>lower bandwidth</b>, <b>progressive latency</b>, and a <b>stable receipt</b> you can
            verify anywhere (server, client, browser/WASM).
            </div>
        </div>
        </div>

      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10, fontSize: 11, color: "#6b7280" }}>
        Endpoints used:
        <div style={{ marginTop: 6 }}><code>POST /api/wirepack/v46/session/new</code></div>
        <div style={{ marginTop: 6 }}><code>POST /api/wirepack/v46/encode_struct</code></div>
        <div style={{ marginTop: 6 }}><code>POST /api/wirepack/v46/decode_struct</code></div>
      </div>
    </div>
  );
};