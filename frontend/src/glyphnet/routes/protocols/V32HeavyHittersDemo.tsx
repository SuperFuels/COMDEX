import React, { useMemo, useState } from "react";

async function fetchJson(url: string, body: any, timeoutMs = 30000) {
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

function safeObj(x: any) {
  return x && typeof x === "object" ? x : {};
}

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function boolBadge(ok: boolean | null) {
  const good = ok === true;
  const bad = ok === false;
  const bg = good ? "#ecfdf5" : bad ? "#fef2f2" : "#f9fafb";
  const fg = good ? "#065f46" : bad ? "#991b1b" : "#6b7280";
  const bd = good ? "#a7f3d0" : bad ? "#fecaca" : "#e5e7eb";
  const label = good ? "✅ VERIFIED" : bad ? "❌ FAIL" : "—";
  return { bg, fg, bd, label };
}

type HH = { idx: number; hits: number };

// stable JSON (deterministic ordering)
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

function utf8Len(s: string): number {
  try {
    return new TextEncoder().encode(s).length;
  } catch {
    return s.length;
  }
}

async function gzipLenUtf8(s: string): Promise<number | null> {
  try {
    // @ts-ignore
    if (typeof CompressionStream === "undefined") return null;
    const u8 = new TextEncoder().encode(s);
    // @ts-ignore
    const stream = new Blob([u8]).stream().pipeThrough(new CompressionStream("gzip"));
    const ab = await new Response(stream).arrayBuffer();
    return new Uint8Array(ab).length;
  } catch {
    return null;
  }
}

async function gzipStreamLenUtf8(parts: string[], sep = "\n"): Promise<number | null> {
  try {
    // @ts-ignore
    if (typeof CompressionStream === "undefined") return null;
    const joined = parts.join(sep);
    const u8 = new TextEncoder().encode(joined);
    // @ts-ignore
    const stream = new Blob([u8]).stream().pipeThrough(new CompressionStream("gzip"));
    const ab = await new Response(stream).arrayBuffer();
    return new Uint8Array(ab).length;
  } catch {
    return null;
  }
}

// Accept lots of backend shapes:
// - [{idx: 69, hits: 2}, ...]
// - [{index: 69, count: 2}, ...]
// - [[69,2], [1671,2], ...]
// - ["idx 69: 2 hits", ...]
function parseTopK(topkAny: any): HH[] {
  const arr = Array.isArray(topkAny) ? topkAny : [];
  const out: HH[] = [];

  for (const x of arr) {
    if (x == null) continue;

    if (Array.isArray(x) && x.length >= 2) {
      const idx = Number(x[0]);
      const hits = Number(x[1]);
      if (Number.isFinite(idx) && Number.isFinite(hits)) out.push({ idx, hits });
      continue;
    }

    if (typeof x === "object") {
      const idx = Number((x as any).idx ?? (x as any).index ?? (x as any).i);
      const hits = Number((x as any).hits ?? (x as any).count ?? (x as any).c ?? (x as any).value);
      if (Number.isFinite(idx) && Number.isFinite(hits)) out.push({ idx, hits });
      continue;
    }

    if (typeof x === "string") {
      // crude parse: "idx 69: 2 hits"
      const m = x.match(/(\d+)[^\d]+(\d+)/);
      if (m) {
        const idx = Number(m[1]);
        const hits = Number(m[2]);
        if (Number.isFinite(idx) && Number.isFinite(hits)) out.push({ idx, hits });
      }
    }
  }

  // Keep deterministic ordering: desc hits, then asc idx
  out.sort((a, b) => (b.hits - a.hits) || (a.idx - b.idx));
  return out;
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

function MiniBarChart(props: { data: HH[]; height?: number; title?: string }) {
  const height = props.height ?? 180;
  const data = props.data.slice(0, 16);
  const max = Math.max(1, ...data.map((d) => d.hits));

  const w = 640;
  const h = height;
  const padL = 44;
  const padR = 16;
  const padT = 18;
  const padB = 48;

  const innerW = w - padL - padR;
  const innerH = h - padT - padB;
  const n = Math.max(1, data.length);
  const barW = innerW / n;

  const y = (v: number) => padT + innerH * (1 - v / max);

  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>
          {props.title ?? "Heavy Hitters (Live)"}
        </div>
        <div style={{ fontSize: 10, color: "#6b7280" }}>
          Bars = hits per index (Top-K). Max={max}
        </div>
      </div>

      {data.length === 0 ? (
        <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280" }}>
          No Top-K array found yet. Run the demo.
        </div>
      ) : (
        <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", marginTop: 8, display: "block" }}>
          <line x1={padL} y1={padT} x2={padL} y2={padT + innerH} stroke="#e5e7eb" />
          <line x1={padL} y1={padT + innerH} x2={padL + innerW} y2={padT + innerH} stroke="#e5e7eb" />

          {[0, max].map((t, i) => (
            <g key={i}>
              <line x1={padL - 4} y1={y(t)} x2={padL} y2={y(t)} stroke="#e5e7eb" />
              <text x={padL - 8} y={y(t) + 4} fontSize="10" textAnchor="end" fill="#6b7280">
                {t}
              </text>
            </g>
          ))}

          {data.map((d, i) => {
            const x = padL + i * barW + Math.max(2, barW * 0.12);
            const bw = Math.max(6, barW * 0.76);
            const top = y(d.hits);
            const bh = padT + innerH - top;

            const fill = d.hits > 1 ? "#ef4444" : "#3b82f6";

            return (
              <g key={`${d.idx}-${i}`}>
                <rect x={x} y={top} width={bw} height={bh} rx={6} fill={fill} opacity={0.9} />
                <text x={x + bw / 2} y={padT + innerH + 14} fontSize="10" textAnchor="middle" fill="#6b7280">
                  {d.idx}
                </text>
                <text x={x + bw / 2} y={top - 6} fontSize="10" textAnchor="middle" fill="#111827">
                  {d.hits}
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}

export const V32HeavyHittersDemo: React.FC = () => {
  const [seed, setSeed] = useState(1337);
  const [n, setN] = useState(4096);
  const [turns, setTurns] = useState(64);
  const [muts, setMuts] = useState(3);
  const [k, setK] = useState(16);

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [out, setOut] = useState<any>(null);

  // verifier
  const [receiptInput, setReceiptInput] = useState("");
  const [showExamples, setShowExamples] = useState(true);

  // baselines (ONLY if backend provides samples)
  const [rawJsonTotalBytes, setRawJsonTotalBytes] = useState<number | null>(null);
  const [gzipPerFrameTotalBytes, setGzipPerFrameTotalBytes] = useState<number | null>(null);
  const [gzipStreamTotalBytes, setGzipStreamTotalBytes] = useState<number | null>(null);
  const [baselineNote, setBaselineNote] = useState<string | null>(null);

  const EXAMPLES = [
    { label: "🎯 Story example (4096/64/3, K=16)", seed: 1337, n: 4096, turns: 64, muts: 3, k: 16 },
    { label: "Sparse fleet (n=50k, fewer turns)", seed: 2026, n: 50_000, turns: 24, muts: 2, k: 10 },
    { label: "Security-ish burst (higher muts)", seed: 9090, n: 100_000, turns: 32, muts: 8, k: 25 },
  ];

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setOut(null);

    setRawJsonTotalBytes(null);
    setGzipPerFrameTotalBytes(null);
    setGzipStreamTotalBytes(null);
    setBaselineNote(null);

    try {
      const body = { seed, n, turns, muts, k };
      const { ok, status, json } = await fetchJson("/api/wirepack/v32/run", body, 60000);
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setOut(json);

      // -------- baseline handling (backend-provided only) --------
      const receiptSamples =
        Array.isArray(json?.receipts?.baseline_samples) ? json.receipts.baseline_samples :
        Array.isArray(json?.receipt?.baseline_samples) ? json.receipt.baseline_samples :
        Array.isArray(json?.baseline_samples) ? json.baseline_samples :
        null;

      if (!receiptSamples || receiptSamples.length === 0) {
        setBaselineNote("Baseline comparison unavailable (backend did not return baseline_samples). Use v46 for real streaming baselines.");
        return;
      }

      const parts: string[] = [];
      for (const s of receiptSamples) {
        if (typeof s === "string") parts.push(s);
        else parts.push(stableStringify(s));
      }

      let rawTotal = 0;
      for (const p of parts) rawTotal += utf8Len(p);
      setRawJsonTotalBytes(rawTotal);

      // per-frame gzip
      let gzFrameKnown = true;
      let gzFrameTotal = 0;
      for (const p of parts) {
        const g = await gzipLenUtf8(p);
        if (g == null) { gzFrameKnown = false; break; }
        gzFrameTotal += g;
      }
      setGzipPerFrameTotalBytes(gzFrameKnown ? gzFrameTotal : null);

      // stream gzip
      const gzStream = await gzipStreamLenUtf8(parts);
      setGzipStreamTotalBytes(gzStream);

      // @ts-ignore
      if (typeof CompressionStream === "undefined") {
        setBaselineNote("Baseline_samples provided, but gzip unsupported in this browser.");
      } else {
        setBaselineNote(`Baselines computed from backend-provided baseline_samples (n=${parts.length}).`);
      }
    } catch (e: any) {
      setErr(e?.message || "Demo failed");
    } finally {
      setBusy(false);
    }
  }

  const invariants = useMemo(() => safeObj(out?.invariants), [out]);
  const receipts = useMemo(() => safeObj(out?.receipts), [out]);
  const b = useMemo(() => safeObj(out?.bytes), [out]);

  const topkAny = out?.topk ?? out?.top_k ?? out?.result?.topk ?? out?.results?.topk ?? out?.answer?.topk ?? null;
  const topkParsed = useMemo(() => parseTopK(topkAny), [topkAny]);

  const heavyOk = (invariants?.topk_ok ?? invariants?.heavy_hitters_ok ?? invariants?.ok ?? null) as any;
  const badge = boolBadge(heavyOk === null ? null : Boolean(heavyOk));

  const drift = String(receipts?.drift_sha256 ?? out?.drift_sha256 ?? "");
  const finalState = String(out?.final_state_sha256 ?? "");

  const leanOk = receipts?.LEAN_OK ?? out?.LEAN_OK ?? null;

  // wire bytes
  const templateBytes =
    b?.wire_template_bytes ??
    b?.template_bytes ??
    0;

  const deltaBytesTotal =
    b?.wire_delta_bytes_total ??
    b?.delta_bytes_total ??
    0;

  const wireTotal =
    b?.wire_total_bytes ??
    (Number(templateBytes || 0) + Number(deltaBytesTotal || 0));

  // perf
  const qMs = out?.timing_ms?.query ?? out?.timing_ms ?? out?.query_ms ?? null;

  const ops = Number(turns || 0) * Number(muts || 0);
  const bytesPerOp = ops > 0 ? Number(deltaBytesTotal || 0) / ops : null;

  // receipt verifier
  const normalizedInput = receiptInput.trim().toLowerCase();
  const normalizedDrift = (drift || "").trim().toLowerCase();
  const receiptMatch = normalizedInput.length >= 8 && normalizedDrift.length >= 8 && normalizedInput === normalizedDrift;
  const receiptBadge = boolBadge(normalizedInput.length === 0 ? null : receiptMatch);

  // baseline comparisons (only if we computed)
  const wireVsRawPct =
    rawJsonTotalBytes != null && rawJsonTotalBytes > 0 ? (Number(wireTotal) / rawJsonTotalBytes - 1) * 100 : null;

  const wireVsGzFramePct =
    gzipPerFrameTotalBytes != null && gzipPerFrameTotalBytes > 0 ? (Number(wireTotal) / gzipPerFrameTotalBytes - 1) * 100 : null;

  const wireVsGzStreamPct =
    gzipStreamTotalBytes != null && gzipStreamTotalBytes > 0 ? (Number(wireTotal) / gzipStreamTotalBytes - 1) * 100 : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 900, color: "#111827" }}>
            v32 — Dashboard Unlock (Heavy Hitters / Top-K)
          </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            Top-K directly on compressed delta streams — no decompression, no full state materialization — with verifiable receipts.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            seed
            <input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value) || 0)}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }} />
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            n
            <input type="number" value={n} onChange={(e) => setN(clamp(Number(e.target.value) || 4096, 256, 1_000_000))}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }} />
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            turns
            <input type="number" value={turns} onChange={(e) => setTurns(clamp(Number(e.target.value) || 64, 1, 4096))}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }} />
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            muts
            <input type="number" value={muts} onChange={(e) => setMuts(clamp(Number(e.target.value) || 3, 1, 4096))}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }} />
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            K
            <input type="number" value={k} onChange={(e) => setK(clamp(Number(e.target.value) || 16, 1, 128))}
              style={{ width: 70, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }} />
          </label>

          <button
            type="button"
            onClick={() => setShowExamples((s) => !s)}
            style={{
              padding: "6px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#fff",
              color: "#111827",
              fontSize: 11,
              fontWeight: 900,
              cursor: "pointer",
            }}
          >
            Examples
          </button>

          <button
            type="button"
            onClick={run}
            style={{
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid " + (busy ? "#e5e7eb" : "#111827"),
              background: busy ? "#f9fafb" : "#111827",
              color: busy ? "#6b7280" : "#fff",
              fontSize: 11,
              fontWeight: 900,
              cursor: busy ? "default" : "pointer",
            }}
          >
            {busy ? "Running…" : "Run"}
          </button>
        </div>
      </div>

      {showExamples ? (
        <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Presets</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
            {EXAMPLES.map((ex) => (
              <button
                key={ex.label}
                type="button"
                onClick={() => { setSeed(ex.seed); setN(ex.n); setTurns(ex.turns); setMuts(ex.muts); setK(ex.k); }}
                style={{
                  padding: "6px 10px",
                  borderRadius: 999,
                  border: "1px solid #e5e7eb",
                  background: "#f9fafb",
                  color: "#111827",
                  fontSize: 11,
                  fontWeight: 900,
                  cursor: "pointer",
                }}
              >
                {ex.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {err ? <div style={{ fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: 10 }}>
        <MiniBarChart data={topkParsed} title="Heavy Hitters (Live)" />

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <StatTile label="Query time" value={qMs != null ? `${Number(qMs).toFixed(2)} ms` : "—"} sub="delta scan + Top-K accumulator" />
          <StatTile label="Stream size" value={bytes(Number(wireTotal || 0))} sub="template + delta stream" />
          <StatTile label="Ops" value={ops ? ops : "—"} sub={`${turns} turns × ${muts} muts`} />
          <StatTile label="Bytes / op" value={bytesPerOp != null ? `${bytesPerOp.toFixed(2)} B` : "—"} sub="delta_bytes_total / ops" />
          <StatTile label="LEAN_OK" value={leanOk != null ? String(leanOk) : "—"} sub="formally checked invariant chain" />
          <StatTile label="topk_ok" value={heavyOk == null ? "—" : heavyOk ? "true ✅" : "false ❌"} sub="order-independent correctness" />
        </div>
      </div>

      {/* Baselines (truthful) */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Baselines (truthful)</div>

        <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
          raw_json_total: <b>{rawJsonTotalBytes == null ? "—" : bytes(rawJsonTotalBytes)}</b>{" "}
          <span style={{ color: "#6b7280" }}>({rawJsonTotalBytes ?? "—"} B)</span>{" "}
          {wireVsRawPct != null ? (
            <span style={{ color: wireVsRawPct <= 0 ? "#065f46" : "#991b1b", fontWeight: 900 }}>
              {" "}({wireVsRawPct > 0 ? "+" : ""}{wireVsRawPct.toFixed(1)}%)
            </span>
          ) : null}
        </div>

        <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
          gzip_per_frame_total: <b>{gzipPerFrameTotalBytes == null ? "—" : bytes(gzipPerFrameTotalBytes)}</b>{" "}
          <span style={{ color: "#6b7280" }}>({gzipPerFrameTotalBytes ?? "—"} B)</span>{" "}
          {wireVsGzFramePct != null ? (
            <span style={{ color: wireVsGzFramePct <= 0 ? "#065f46" : "#991b1b", fontWeight: 900 }}>
              {" "}({wireVsGzFramePct > 0 ? "+" : ""}{wireVsGzFramePct.toFixed(1)}%)
            </span>
          ) : (
            <span style={{ color: "#6b7280" }}> (unavailable)</span>
          )}
        </div>

        <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
          gzip_stream_total: <b>{gzipStreamTotalBytes == null ? "—" : bytes(gzipStreamTotalBytes)}</b>{" "}
          <span style={{ color: "#6b7280" }}>({gzipStreamTotalBytes ?? "—"} B)</span>{" "}
          {wireVsGzStreamPct != null ? (
            <span style={{ color: wireVsGzStreamPct <= 0 ? "#065f46" : "#991b1b", fontWeight: 900 }}>
              {" "}({wireVsGzStreamPct > 0 ? "+" : ""}{wireVsGzStreamPct.toFixed(1)}%)
            </span>
          ) : (
            <span style={{ color: "#6b7280" }}> (unavailable)</span>
          )}
        </div>

        <div style={{ marginTop: 8, fontSize: 10, color: "#6b7280" }}>
          {baselineNote ? baselineNote : "Baselines require backend-provided baseline_samples (or use v46 for real streaming)."}
        </div>
      </div>

      {/* Receipt verifier */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Receipt verifier</div>
          <div
            style={{
              padding: "6px 10px",
              borderRadius: 999,
              border: `1px solid ${receiptBadge.bd}`,
              background: receiptBadge.bg,
              color: receiptBadge.fg,
              fontSize: 11,
              fontWeight: 900,
            }}
          >
            {receiptBadge.label}
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 10, alignItems: "center" }}>
          <input
            value={receiptInput}
            onChange={(e) => setReceiptInput(e.target.value)}
            placeholder="Paste drift_sha256 here to verify…"
            style={{
              flex: "1 1 420px",
              padding: "10px 12px",
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              fontSize: 12,
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            }}
          />
          <button
            type="button"
            onClick={() => setReceiptInput(drift || "")}
            style={{
              padding: "8px 10px",
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              color: "#111827",
              fontSize: 11,
              fontWeight: 900,
              cursor: "pointer",
            }}
            title="Copy current drift into the verifier input"
          >
            Use current drift
          </button>
        </div>

        <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280", lineHeight: 1.55 }}>
          <div>
            drift_sha256 (from run):{" "}
            <code style={{ color: "#111827" }}>{drift || "—"}</code>
          </div>
          <div style={{ marginTop: 4 }}>
            Any verifier can re-run Top-K over the same delta stream and recompute this hash. Match = “dashboard is provably correct”.
          </div>
        </div>
      </div>

      {out ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Invariant status</div>
              <div
                style={{
                  padding: "6px 10px",
                  borderRadius: 999,
                  border: `1px solid ${badge.bd}`,
                  background: badge.bg,
                  color: badge.fg,
                  fontSize: 11,
                  fontWeight: 900,
                }}
              >
                {badge.label}
              </div>
            </div>

            <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
              {Object.keys(invariants).length ? (
                Object.keys(invariants).sort().map((k) => (
                  <div key={k}>
                    {k}: <code>{String(invariants[k])}</code>
                  </div>
                ))
              ) : (
                <div style={{ color: "#6b7280" }}>No invariants object returned (see raw JSON below).</div>
              )}
            </div>

            <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid #e5e7eb" }}>
              <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Top-K (heavy hitters)</div>
              {topkParsed.length ? (
                <ul style={{ margin: "8px 0 0 16px", padding: 0, fontSize: 11, color: "#374151" }}>
                  {topkParsed.slice(0, 32).map((x, i) => (
                    <li key={`${x.idx}-${i}`}>
                      <code>idx {x.idx}: {x.hits} hit{x.hits === 1 ? "" : "s"}</code>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
                  (No <code>topk</code> array found — check Raw response.)
                </div>
              )}
            </div>
          </div>

          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Receipt</div>
            <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
              <div>template_bytes: <code>{bytes(Number(templateBytes || 0))}</code></div>
              <div>delta_bytes_total: <code>{bytes(Number(deltaBytesTotal || 0))}</code></div>
              <div>wire_total_bytes: <code>{bytes(Number(wireTotal || 0))}</code></div>

              <div style={{ paddingTop: 8, borderTop: "1px solid #e5e7eb", marginTop: 8 }}>
                final_state_sha256: <code>{finalState || "—"}</code>
              </div>
              <div>drift_sha256: <code>{drift || "—"}</code></div>
              <div>LEAN_OK: <code>{String(leanOk)}</code></div>
            </div>
          </div>

          <div style={{ gridColumn: "1 / -1", borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Raw response</div>
            <pre style={{ marginTop: 8, fontSize: 11, color: "#111827", whiteSpace: "pre-wrap" }}>
              {JSON.stringify(out, null, 2)}
            </pre>
          </div>
        </div>
      ) : null}

      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10, fontSize: 11, color: "#6b7280" }}>
        Endpoint used:
        <div style={{ marginTop: 6 }}>
          <code>POST /api/wirepack/v32/run</code>
        </div>
      </div>
    </div>
  );
};