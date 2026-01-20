import React, { useMemo, useState } from "react";

// -------------------------------
// tiny helpers (drop-in)
// -------------------------------

const BRAND = {
  pageBg: "#F8FAFC",          // light slate
  cardBg: "#FFFFFF",
  border: "#E2E8F0",          // slate-200
  soft: "#F1F5F9",            // slate-100
  soft2: "#F8FAFC",           // slate-50
  text: "#0F172A",            // slate-900
  text2: "#334155",           // slate-700
  muted: "#64748B",           // slate-500
  accent: "#1B74E4",          // blue
  accentSoft: "rgba(27,116,228,0.10)",
  shadow: "0 1px 2px rgba(15,23,42,0.06)",
};

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

async function fetchJsonWithTimeout(url: string, init: RequestInit = {}, timeoutMs = 15000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, { ...init, signal: ctrl.signal });
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

function tri(ok: boolean | null) {
  if (ok === null) return { label: "—", color: BRAND.muted, bg: BRAND.soft2, bd: BRAND.border, icon: "•" };
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
    border: "1px solid " + (active ? BRAND.accent : BRAND.border),
    background: active ? BRAND.accent : BRAND.cardBg,
    color: active ? "#fff" : BRAND.text,
    fontSize: 11,
    fontWeight: 900 as const,
    cursor: "pointer",
    whiteSpace: "nowrap" as const,
    boxShadow: active ? BRAND.shadow : undefined,
  };
}

function cardStyle() {
  return {
    borderRadius: 16,
    border: `1px solid ${BRAND.border}`,
    background: BRAND.cardBg,
    padding: 12,
    boxShadow: BRAND.shadow,
  };
}

function miniLabel() {
  return { fontSize: 11, color: BRAND.text2, fontWeight: 900 as const };
}

function miniText() {
  return { fontSize: 11, color: BRAND.muted, lineHeight: 1.45 };
}

// -------------------------------
// API
// -------------------------------

type V38Resp = {
  ok: boolean;
  demo?: string;
  params?: { seed: number; n: number; turns: number; muts: number };
  bytes?: {
    wire_template_bytes: number;
    wire_delta_bytes_total: number;
    wire_total_bytes: number;
    rawA_bytes_total: number;
    rawB_bytes_total: number;
    canon_bytes_total: number;
  };
  invariants?: { canon_ok: boolean; replay_ok: boolean };
  final_state_sha256?: string;
  receipts?: { final_state_sha256: string; drift_sha256: string; LEAN_OK: number };
  error?: string;
};

async function runV38(seed: number, n: number, turns: number, muts: number): Promise<V38Resp> {
  const { ok, status, json } = await fetchJsonWithTimeout(
    "/api/wirepack/v38/run",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seed, n, turns, muts }),
    },
    30000,
  );
  if (!ok) throw new Error(`v38/run HTTP ${status}: ${JSON.stringify(json)}`);
  return json as V38Resp;
}

// -------------------------------
// mini graph (raw vs canon + template/deltas split)
// -------------------------------

function svgV38Graph(opts: {
  rawA: number;
  rawB: number;
  canon: number;
  template: number;
  deltas: number;
  total: number;
  n: number;
  turns: number;
  muts: number;
  height?: number;
}) {
  const { rawA, rawB, canon, template, deltas, total, n, turns, muts, height = 230 } = opts;

  const W = 900;
  const H = height;
  const pad = 18;

  const plotW = W - pad * 2;
  const plotH = H - pad * 2;

  const x0 = pad;
  const y0 = pad;

  const headerY = y0 + 10;
  const barTop = y0 + 34;
  const barH = Math.max(16, Math.round(plotH * 0.10));
  const barGap = 10;

  const maxRaw = Math.max(1, rawA || 0, rawB || 0, canon || 0);
  const scale = (v: number) => Math.max(4, Math.round((plotW * Math.max(0, v)) / maxRaw));

  const bars = [
    {
      name: "rawA bytes",
      v: rawA,
      fill: BRAND.soft2,
      stroke: BRAND.border,
      fill2: BRAND.soft,
      stroke2: "#CBD5E1", // slate-300
    },
    {
      name: "rawB bytes",
      v: rawB,
      fill: BRAND.soft2,
      stroke: BRAND.border,
      fill2: BRAND.soft,
      stroke2: "#CBD5E1",
    },
    {
      name: "canon bytes",
      v: canon,
      fill: BRAND.soft2,
      stroke: BRAND.border,
      fill2: BRAND.accentSoft,
      stroke2: "#93C5FD", // blue-300
    },
  ];

  const footprintY = barTop + bars.length * (barH + barGap) + 12;
  const footprintH = Math.max(18, Math.round(plotH * 0.14));

  const tot = Math.max(1, total || template + deltas || 1);
  const tFrac = Math.max(0, Math.min(1, (template || 0) / tot));
  const dFrac = Math.max(0, Math.min(1, (deltas || 0) / tot));
  const tW = Math.round(plotW * tFrac);
  const dW = Math.round(plotW * dFrac);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="v38 reorder vs canonical graph">
      <rect x={0} y={0} width={W} height={H} rx={16} ry={16} fill={BRAND.cardBg} />
      <rect x={x0} y={y0} width={plotW} height={plotH} rx={12} ry={12} fill="transparent" stroke={BRAND.border} />

      <text x={x0} y={headerY} fontSize={11} fill={BRAND.muted}>
        Reordering changes raw bytes; canonicalization produces a stable byte artifact. Below: transport split (template vs deltas).
      </text>

      {bars.map((b, i) => {
        const y = barTop + i * (barH + barGap);
        const w = scale(b.v);
        return (
          <g key={b.name}>
            <rect x={x0} y={y} width={plotW} height={barH} rx={12} ry={12} fill={b.fill} stroke={b.stroke} />
            <rect x={x0} y={y} width={w} height={barH} rx={12} ry={12} fill={b.fill2} stroke={b.stroke2} />
            <text x={x0 + 10} y={y + barH / 2 + 4} fontSize={11} fill={BRAND.text2}>
              {b.name}
            </text>
            <text x={x0 + plotW - 10} y={y + barH / 2 + 4} fontSize={11} fill={BRAND.text2} textAnchor="end">
              {Number(b.v || 0).toLocaleString()} B
            </text>
          </g>
        );
      })}

      {/* footprint */}
      <text x={x0} y={footprintY - 6} fontSize={11} fill={BRAND.muted}>
        Wire footprint split: template bytes vs delta bytes (total transport)
      </text>
      <rect x={x0} y={footprintY} width={plotW} height={footprintH} rx={12} ry={12} fill={BRAND.soft2} stroke={BRAND.border} />
      <rect x={x0} y={footprintY} width={Math.max(2, tW)} height={footprintH} rx={12} ry={12} fill="#DBEAFE" stroke="#93C5FD" />
      <rect
        x={x0 + Math.max(2, tW)}
        y={footprintY}
        width={Math.max(2, dW)}
        height={footprintH}
        rx={12}
        ry={12}
        fill="#ECFEFF"
        stroke="#A5F3FC"
      />

      <text x={x0} y={footprintY + footprintH + 14} fontSize={11} fill={BRAND.muted}>
        n={n.toLocaleString()} · turns={turns.toLocaleString()} · muts={muts.toLocaleString()}
      </text>
      <text x={x0 + plotW} y={footprintY + footprintH + 14} fontSize={11} fill={BRAND.muted} textAnchor="end">
        template={bytes(template)} · deltas={bytes(deltas)} · total={bytes(tot)}
      </text>
    </svg>
  );
}

// -------------------------------
// component
// -------------------------------

export const V38TrustReceiptsDemo: React.FC = () => {
  // params
  const [seed, setSeed] = useState<number>(1337);
  const [n, setN] = useState<number>(4096);
  const [turns, setTurns] = useState<number>(64);
  const [muts, setMuts] = useState<number>(3);

  // UI
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [resp, setResp] = useState<V38Resp | null>(null);
  const [showRaw, setShowRaw] = useState(false);

  // derived
  const inv = resp?.invariants;
  const canonOk = inv?.canon_ok == null ? null : Boolean(inv.canon_ok);
  const replayOk = inv?.replay_ok == null ? null : Boolean(inv.replay_ok);

  const leanOkVal = resp?.receipts?.LEAN_OK;
  const leanOk = leanOkVal == null ? null : Number(leanOkVal) === 1;

  const b = resp?.bytes;
  const template = Number(b?.wire_template_bytes ?? 0);
  const deltas = Number(b?.wire_delta_bytes_total ?? 0);
  const total = Number(b?.wire_total_bytes ?? (template + deltas));

  const rawA = Number(b?.rawA_bytes_total ?? 0);
  const rawB = Number(b?.rawB_bytes_total ?? 0);
  const canon = Number(b?.canon_bytes_total ?? 0);

  const deltaPct = useMemo(() => {
    if (!total) return null;
    return (100 * (deltas / total)).toFixed(1);
  }, [total, deltas]);

  const opsTotal = useMemo(() => Math.max(0, Math.floor(Number(turns || 0) * Number(muts || 0))), [turns, muts]);
  const bytesPerOp = useMemo(() => (opsTotal > 0 ? total / opsTotal : 0), [total, opsTotal]);

  const curl = useMemo(() => {
    const bodyStr = JSON.stringify({ seed, n, turns, muts });
    return `curl -sS -X POST http://127.0.0.1:8787/api/wirepack/v38/run \\
  -H 'content-type: application/json' \\
  -d '${bodyStr}' | jq`;
  }, [seed, n, turns, muts]);

  function applyPreset(which: "balanced" | "stress" | "tiny") {
    if (which === "balanced") {
      setSeed(1337);
      setN(4096);
      setTurns(64);
      setMuts(3);
    } else if (which === "stress") {
      setSeed(9001);
      setN(65536);
      setTurns(256);
      setMuts(32);
    } else {
      setSeed(42);
      setN(2048);
      setTurns(32);
      setMuts(2);
    }
  }

  async function copyText(s: string) {
    try {
      await navigator.clipboard.writeText(s);
    } catch {
      // ignore
    }
  }

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setResp(null);
    try {
      const out = await runV38(seed, n, turns, muts);
      setResp(out);
    } catch (e: any) {
      setErr(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ ...cardStyle(), padding: 14 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 900, color: BRAND.text }}>
            v38 — canonical bytes + replay invariants{" "}
            <span style={{ fontSize: 11, fontWeight: 900, color: BRAND.muted }}>· trust & receipts</span>
          </div>
          <div style={{ fontSize: 11, color: BRAND.muted, marginTop: 3, maxWidth: 860 }}>
            Same logical ops, different ordering → <b>canonical bytes identical</b>. Replay → <b>final state hash identical</b>. Emits deterministic receipts.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <Badge ok={canonOk} label={`canon_ok: ${canonOk === true ? "OK" : canonOk === false ? "FAIL" : "—"}`} />
          <Badge ok={replayOk} label={`replay_ok: ${replayOk === true ? "OK" : replayOk === false ? "FAIL" : "—"}`} />
          <Badge ok={leanOk} label={`LEAN: ${leanOk === true ? "OK" : leanOk === false ? "FAIL" : "—"}`} />

          <button
            type="button"
            onClick={run}
            disabled={busy}
            style={{
              padding: "7px 12px",
              borderRadius: 999,
              border: `1px solid ${busy ? BRAND.border : BRAND.accent}`,
              background: busy ? BRAND.soft : BRAND.accent,
              color: busy ? BRAND.muted : "#fff",
              fontSize: 11,
              fontWeight: 900,
              cursor: busy ? "not-allowed" : "pointer",
              boxShadow: busy ? undefined : BRAND.shadow,
            }}
          >
            {busy ? "Running…" : "Run"}
          </button>
        </div>
      </div>

      {/* Presets + quick actions */}
      <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontSize: 11, color: BRAND.muted, fontWeight: 900 }}>Presets</span>
        <button type="button" onClick={() => applyPreset("balanced")} style={pillStyle(false)}>
          Balanced
        </button>
        <button type="button" onClick={() => applyPreset("stress")} style={pillStyle(false)}>
          Stress
        </button>
        <button type="button" onClick={() => applyPreset("tiny")} style={pillStyle(false)}>
          Tiny
        </button>

        <span style={{ width: 1, height: 18, background: BRAND.border, marginLeft: 6, marginRight: 6 }} />

        <button type="button" onClick={() => copyText(curl)} style={pillStyle(false)} title="Copy reproducible curl">
          Copy curl
        </button>

        <label style={{ display: "inline-flex", gap: 8, alignItems: "center", fontSize: 11, fontWeight: 900, color: BRAND.text }}>
          <input type="checkbox" checked={showRaw} onChange={(e) => setShowRaw(e.target.checked)} />
          Raw JSON
        </label>
      </div>

      {err ? <div style={{ marginTop: 10, fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

      {/* 3-column layout */}
      <div
        style={{
          marginTop: 12,
          display: "grid",
          gridTemplateColumns: "minmax(260px, 320px) minmax(420px, 1fr) minmax(260px, 340px)",
          gap: 12,
        }}
      >
        {/* Left: seller-style pitch (NO fake seller fields) */}
        <div style={{ ...cardStyle() }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: BRAND.text }}>🔥 Trust unlock</div>
            <div style={{ fontSize: 10, color: BRAND.muted, fontWeight: 900 }}>deterministic receipts under reordering</div>
          </div>

          <div style={{ marginTop: 8, ...miniText() }}>
            <b>The claim:</b> the same logical update-set produces <b>bit-identical canonical bytes</b> and the <b>same final state hash</b>,
            even if messages arrive in different orders.
          </div>

          <div style={{ marginTop: 10, fontSize: 11, color: BRAND.text2, lineHeight: 1.55 }}>
            <div>
              <b>This run shape:</b> n=<b>{n.toLocaleString()}</b>, turns=<b>{turns.toLocaleString()}</b>, muts=<b>{muts.toLocaleString()}</b>{" "}
              → ops≈<b>{opsTotal.toLocaleString()}</b>
            </div>

            <div style={{ marginTop: 10, borderRadius: 14, border: `1px solid ${BRAND.border}`, background: BRAND.soft2, padding: 10 }}>
              <div style={{ ...miniLabel() }}>Outputs you can pin (this run)</div>
              <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr", gap: 6 }}>
                <div>
                  canon bytes: <b style={{ color: BRAND.text }}>{canon ? `${canon.toLocaleString()} B` : "—"}</b>
                </div>
                <div>
                  final_state_sha256:{" "}
                  <span style={{ color: BRAND.muted }}>
                    {resp?.receipts?.final_state_sha256
                      ? resp.receipts.final_state_sha256.slice(0, 10) + "…"
                      : resp?.final_state_sha256
                        ? resp.final_state_sha256.slice(0, 10) + "…"
                        : "—"}
                  </span>
                </div>
                <div>
                  drift_sha256:{" "}
                  <span style={{ color: BRAND.muted }}>
                    {resp?.receipts?.drift_sha256 ? resp.receipts.drift_sha256.slice(0, 10) + "…" : "—"}
                  </span>
                </div>
                <div>
                  wire total: <b style={{ color: BRAND.text }}>{bytes(total)}</b>{" "}
                  <span style={{ color: BRAND.muted }}>({bytesPerOp ? `${bytesPerOp.toFixed(2)} B/op` : "—"})</span>
                </div>
              </div>
            </div>

            <div style={{ marginTop: 10 }}>
              <b>Why it matters:</b> stable receipts enable auditability, caching/dedupe, and eliminate order attacks. A verifier needs <b>bytes + hash</b>, not your runtime.
              <br />
              <b>Lean note:</b> <code>LEAN_OK=1</code> means both invariants held (machine-checkable end-to-end).
            </div>
          </div>

          <div style={{ marginTop: 10, borderTop: `1px solid ${BRAND.border}`, paddingTop: 10 }}>
            <div style={{ ...miniLabel() }}>Endpoint</div>
            <div style={{ marginTop: 6, fontSize: 11, color: BRAND.muted }}>
              <code>POST /api/wirepack/v38/run</code>
            </div>
          </div>
        </div>

        {/* Middle: controls + graph + metric tiles */}
        <div style={{ ...cardStyle() }}>
          {/* Controls */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 8 }}>
            <label style={{ fontSize: 11, color: BRAND.text2 }}>
              seed
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value) || 0)}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: `1px solid ${BRAND.border}` }}
              />
            </label>

            <label style={{ fontSize: 11, color: BRAND.text2 }}>
              n
              <input
                type="number"
                value={n}
                min={256}
                max={1 << 16}
                onChange={(e) => setN(clamp(Number(e.target.value) || 4096, 256, 1 << 16))}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: `1px solid ${BRAND.border}` }}
              />
            </label>

            <label style={{ fontSize: 11, color: BRAND.text2 }}>
              turns
              <input
                type="number"
                value={turns}
                min={1}
                max={4096}
                onChange={(e) => setTurns(clamp(Number(e.target.value) || 64, 1, 4096))}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: `1px solid ${BRAND.border}` }}
              />
            </label>

            <label style={{ fontSize: 11, color: BRAND.text2 }}>
              muts
              <input
                type="number"
                value={muts}
                min={1}
                max={512}
                onChange={(e) => setMuts(clamp(Number(e.target.value) || 3, 1, 512))}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: `1px solid ${BRAND.border}` }}
              />
            </label>
          </div>

          {/* Graph */}
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: BRAND.text }}>Reorder vs canonical graph</div>
              <div style={{ fontSize: 11, color: BRAND.text2 }}>
                canon_ok: <b style={{ color: tri(canonOk).color }}>{tri(canonOk).label}</b>
                {"  "}· replay_ok: <b style={{ color: tri(replayOk).color }}>{tri(replayOk).label}</b>
                {"  "}· LEAN: <b style={{ color: tri(leanOk).color }}>{tri(leanOk).label}</b>
              </div>
            </div>

            <div style={{ marginTop: 10 }}>
              {resp ? (
                <div style={{ borderRadius: 16, border: `1px solid ${BRAND.border}`, overflow: "hidden" }}>
                  {svgV38Graph({
                    rawA,
                    rawB,
                    canon,
                    template,
                    deltas,
                    total,
                    n,
                    turns,
                    muts,
                    height: 230,
                  })}
                </div>
              ) : (
                <div style={{ borderRadius: 16, border: `1px dashed ${BRAND.border}`, background: BRAND.soft2, padding: 14, fontSize: 11, color: BRAND.muted }}>
                  No output yet — hit <b>Run</b>.
                </div>
              )}
            </div>

            <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              <div style={{ borderRadius: 14, border: `1px solid ${BRAND.border}`, background: BRAND.cardBg, padding: 10 }}>
                <div style={{ ...miniLabel() }}>Transport footprint</div>
                <div style={{ marginTop: 6, fontSize: 11, color: BRAND.text2 }}>
                  total: <b style={{ color: BRAND.text }}>{bytes(total)}</b>{" "}
                  <span style={{ color: BRAND.muted }}>
                    (template {bytes(template)} · deltas {bytes(deltas)}{deltaPct ? ` · ~${deltaPct}% deltas` : ""})
                  </span>
                </div>
              </div>

              <div style={{ borderRadius: 14, border: `1px solid ${BRAND.border}`, background: BRAND.cardBg, padding: 10 }}>
                <div style={{ ...miniLabel() }}>Work shape</div>
                <div style={{ marginTop: 6, fontSize: 11, color: BRAND.text2 }}>
                  ops: <b style={{ color: BRAND.text }}>{opsTotal.toLocaleString()}</b>{" "}
                  <span style={{ color: BRAND.muted }}>({bytesPerOp ? `${bytesPerOp.toFixed(2)} B/op` : "—"})</span>
                </div>
              </div>

              <div style={{ borderRadius: 14, border: `1px solid ${BRAND.border}`, background: BRAND.cardBg, padding: 10 }}>
                <div style={{ ...miniLabel() }}>Receipt</div>
                <div style={{ marginTop: 6, fontSize: 11, color: BRAND.text2 }}>
                  drift:{" "}
                  <span style={{ color: BRAND.muted }}>
                    {resp?.receipts?.drift_sha256 ? resp.receipts.drift_sha256.slice(0, 10) + "…" : "—"}
                  </span>
                </div>
              </div>
            </div>

            <div style={{ marginTop: 10, fontSize: 10, color: BRAND.muted }}>
              Raw orderings (<code>rawA</code>, <code>rawB</code>) are order-sensitive. Canonicalization produces an order-invariant byte artifact (<code>canon</code>).
            </div>
          </div>

          {/* Output cards */}
          {resp ? (
            <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div style={{ borderRadius: 16, border: `1px solid ${BRAND.border}`, padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: BRAND.text, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                  Invariants
                  <Badge ok={canonOk} label={`canon_ok: ${canonOk === true ? "OK" : canonOk === false ? "FAIL" : "—"}`} />
                  <Badge ok={replayOk} label={`replay_ok: ${replayOk === true ? "OK" : replayOk === false ? "FAIL" : "—"}`} />
                </div>

                <div style={{ marginTop: 8, fontSize: 11, color: BRAND.text2, lineHeight: 1.6 }}>
                  <div>
                    canon_ok: <code>{String(inv?.canon_ok)}</code>
                  </div>
                  <div>
                    replay_ok: <code>{String(inv?.replay_ok)}</code>
                  </div>
                  <div style={{ marginTop: 10, fontWeight: 900, color: BRAND.text }}>Bytes</div>
                  <div>
                    rawA_bytes_total: <code>{rawA.toLocaleString()} B</code>
                  </div>
                  <div>
                    rawB_bytes_total: <code>{rawB.toLocaleString()} B</code>
                  </div>
                  <div>
                    canon_bytes_total: <code>{canon.toLocaleString()} B</code>
                  </div>
                </div>
              </div>

              <div style={{ borderRadius: 16, border: `1px solid ${BRAND.border}`, padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: BRAND.text, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                  Receipt
                  <Badge ok={leanOk} label={`LEAN_OK: ${resp?.receipts?.LEAN_OK ?? "—"}`} />
                </div>

                <div style={{ marginTop: 8, fontSize: 11, color: BRAND.text2, lineHeight: 1.6 }}>
                  <div style={{ color: BRAND.muted }}>
                    final_state_sha256:{" "}
                    <code style={{ wordBreak: "break-all", color: BRAND.text }}>
                      {resp?.receipts?.final_state_sha256 || resp?.final_state_sha256 || "—"}
                    </code>
                  </div>

                  <div style={{ marginTop: 8, color: BRAND.muted }}>
                    drift_sha256:{" "}
                    <code style={{ wordBreak: "break-all", color: BRAND.text }}>{resp?.receipts?.drift_sha256 || "—"}</code>
                  </div>

                  <div style={{ marginTop: 10, fontWeight: 900, color: BRAND.text }}>Wire</div>
                  <div>
                    template: <b style={{ color: BRAND.text }}>{bytes(template)}</b>{" "}
                    <span style={{ color: BRAND.muted }}>{b?.wire_template_bytes != null ? `(${b.wire_template_bytes} B)` : ""}</span>
                  </div>
                  <div>
                    deltas: <b style={{ color: BRAND.text }}>{bytes(deltas)}</b>{" "}
                    <span style={{ color: BRAND.muted }}>{b?.wire_delta_bytes_total != null ? `(${b.wire_delta_bytes_total} B)` : ""}</span>
                  </div>
                  <div>
                    total: <b style={{ color: BRAND.text }}>{bytes(total)}</b>{" "}
                    <span style={{ color: BRAND.muted }}>{b?.wire_total_bytes != null ? `(${b.wire_total_bytes} B)` : ""}</span>
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {resp && showRaw ? (
            <div style={{ marginTop: 12, borderRadius: 16, border: `1px solid ${BRAND.border}`, padding: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: BRAND.text }}>Raw response</div>
              <pre style={{ marginTop: 8, fontSize: 11, color: BRAND.text, whiteSpace: "pre-wrap" }}>{JSON.stringify(resp, null, 2)}</pre>
            </div>
          ) : null}
        </div>

        {/* Right: what’s special + reproducible command */}
        <div style={{ ...cardStyle() }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: BRAND.text }}>What’s so special?</div>
            <div style={{ fontSize: 10, color: BRAND.muted, fontWeight: 900 }}>why v38 matters</div>
          </div>

          <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
            <div style={{ borderRadius: 14, border: `1px solid ${BRAND.border}`, background: BRAND.soft2, padding: 10 }}>
              <div style={{ ...miniLabel() }}>1) Order attacks die here</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                Reordering can’t change canonical bytes or the final state hash. That’s the trust primitive for distributed ingestion.
              </div>
            </div>

            <div style={{ borderRadius: 14, border: `1px solid ${BRAND.border}`, background: BRAND.soft2, padding: 10 }}>
              <div style={{ ...miniLabel() }}>2) Receipts become artifacts</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                <code>canon_ok</code> pins stable bytes; <code>replay_ok</code> pins stable meaning. Together they make receipts verifiable, cacheable objects.
              </div>
            </div>

            <div style={{ borderRadius: 14, border: `1px solid ${BRAND.border}`, background: BRAND.soft2, padding: 10 }}>
              <div style={{ ...miniLabel() }}>3) Zero-trust verification</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                A verifier only needs <b>canonical bytes</b> + <b>hash</b>. No need to trust your logs or runtime.
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: BRAND.text2 }}>
                <code>LEAN_OK</code> means invariants held end-to-end.
              </div>
            </div>

            <div style={{ borderRadius: 14, border: `1px solid ${BRAND.border}`, background: BRAND.cardBg, padding: 10 }}>
              <div style={{ ...miniLabel() }}>Reproducible command</div>
              <pre style={{ marginTop: 8, fontSize: 10, color: BRAND.text, whiteSpace: "pre-wrap" }}>{curl}</pre>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          marginTop: 12,
          borderRadius: 16,
          border: `1px solid ${BRAND.border}`,
          background: BRAND.soft2,
          padding: 10,
          fontSize: 11,
          color: BRAND.muted,
          display: "flex",
          justifyContent: "space-between",
          gap: 10,
          flexWrap: "wrap",
        }}
      >
        <div>
          endpoint: <code style={{ color: BRAND.text }}>POST /api/wirepack/v38/run</code>
        </div>
        <div>
          wire: <b style={{ color: BRAND.text }}>{bytes(total)}</b>{" "}
          <span style={{ color: BRAND.muted }}>
            · ops {opsTotal.toLocaleString()} · bytes/op {bytesPerOp ? bytesPerOp.toFixed(2) : "—"}
          </span>
        </div>
      </div>
    </div>
  );
};