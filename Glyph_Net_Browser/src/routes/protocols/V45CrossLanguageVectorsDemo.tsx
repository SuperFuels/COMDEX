import React, { useMemo, useState } from "react";

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
      json = { _nonJson: true, _text: txt.slice(0, 300) };
    }
    return { ok: r.ok, status: r.status, json };
  } finally {
    clearTimeout(t);
  }
}

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

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
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

/**
 * v45 graph: five boolean checks as bars + size footprint.
 * (No “work band” because v45 backend typically does not emit work counters.)
 */
function svgPolyglotGraph(opts: {
  checks: Array<{ name: string; ok: boolean | null }>;
  templateBytes: number;
  deltaBytes: number;
  n: number;
  turns: number;
  muts: number;
  height?: number;
}) {
  const { checks, templateBytes, deltaBytes, n, turns, muts, height = 220 } = opts;
  const W = 900;
  const H = height;
  const pad = 18;
  const plotW = W - pad * 2;
  const plotH = H - pad * 2;

  const x0 = pad;
  const y0 = pad;

  const headerY = y0 + 10;
  const barsTop = y0 + 34;
  const barH = Math.max(16, Math.round(plotH * 0.10));
  const barGap = 10;

  // footprint band
  const footprintY = barsTop + checks.length * (barH + barGap) + 10;
  const footprintH = Math.max(18, Math.round(plotH * 0.14));

  const total = Math.max(1, Number(templateBytes || 0) + Number(deltaBytes || 0));
  const tFrac = Math.max(0, Math.min(1, Number(templateBytes || 0) / total));
  const dFrac = Math.max(0, Math.min(1, Number(deltaBytes || 0) / total));

  const tW = Math.round(plotW * tFrac);
  const dW = Math.round(plotW * dFrac);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="Polyglot identity graph">
      <rect x={0} y={0} width={W} height={H} rx={16} ry={16} fill="#fff" />
      <rect x={x0} y={y0} width={plotW} height={plotH} rx={12} ry={12} fill="transparent" stroke="#e5e7eb" />

      <text x={x0} y={headerY} fontSize={11} fill="#6b7280">
        Byte identity checklist (Python ↔ Node) + footprint (template vs deltas)
      </text>

      {checks.map((c, i) => {
        const y = barsTop + i * (barH + barGap);
        const t = tri(c.ok);
        return (
          <g key={c.name}>
            <rect x={x0} y={y} width={plotW} height={barH} rx={12} ry={12} fill="#f9fafb" stroke="#e5e7eb" />
            {/* fill */}
            <rect x={x0} y={y} width={plotW} height={barH} rx={12} ry={12} fill={t.bg} stroke={t.bd} />
            <text x={x0 + 10} y={y + barH / 2 + 4} fontSize={11} fill={t.color}>
              {t.icon} {c.name}
            </text>
            <text x={x0 + plotW - 10} y={y + barH / 2 + 4} fontSize={11} fill={t.color} textAnchor="end">
              {t.label}
            </text>
          </g>
        );
      })}

      {/* footprint band */}
      <text x={x0} y={footprintY - 6} fontSize={11} fill="#6b7280">
        Footprint split: template bytes vs delta bytes (total transport)
      </text>
      <rect x={x0} y={footprintY} width={plotW} height={footprintH} rx={12} ry={12} fill="#f9fafb" stroke="#e5e7eb" />
      <rect x={x0} y={footprintY} width={Math.max(2, tW)} height={footprintH} rx={12} ry={12} fill="#eef2ff" stroke="#c7d2fe" />
      <rect
        x={x0 + Math.max(2, tW)}
        y={footprintY}
        width={Math.max(2, dW)}
        height={footprintH}
        rx={12}
        ry={12}
        fill="#ecfeff"
        stroke="#a5f3fc"
      />

      <text x={x0} y={footprintY + footprintH + 14} fontSize={11} fill="#6b7280">
        n={n.toLocaleString()} · turns={turns.toLocaleString()} · muts={muts.toLocaleString()}
      </text>
      <text x={x0 + plotW} y={footprintY + footprintH + 14} fontSize={11} fill="#6b7280" textAnchor="end">
        template={bytes(templateBytes)} · deltas={bytes(deltaBytes)} · total={bytes(total)}
      </text>
    </svg>
  );
}

export const V45CrossLanguageVectorsDemo: React.FC = () => {
  // params
  const [seed, setSeed] = useState(1337);
  const [n, setN] = useState(256);
  const [turns, setTurns] = useState(16);
  const [muts, setMuts] = useState(128);

  // seller panel knobs
  const [sellerName, setSellerName] = useState("Seller");
  const [sku, setSku] = useState("SKU-GLYPH-45");
  const [audience, setAudience] = useState(2500);
  const [price, setPrice] = useState(19);
  const [showRaw, setShowRaw] = useState(false);

  // run state
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [out, setOut] = useState<any | null>(null);

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setOut(null);
    try {
      const { ok, status, json } = await fetchJson("/api/wirepack/v45/run", { seed, n, turns, muts }, 30000);
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setOut(json);
    } catch (e: any) {
      setErr(e?.message || "Demo failed");
    } finally {
      setBusy(false);
    }
  }

  function applyPreset(which: "balanced" | "stress" | "tiny") {
    if (which === "balanced") {
      setSeed(1337);
      setN(256);
      setTurns(16);
      setMuts(128);
    } else if (which === "stress") {
      setSeed(9001);
      setN(2048);
      setTurns(64);
      setMuts(256);
    } else {
      setSeed(42);
      setN(256);
      setTurns(8);
      setMuts(64);
    }
  }

  // parse outputs
  const inv = out?.invariants || {};
  const b = out?.bytes || {};
  const receipts = out?.receipts || {};

  const leanOkVal = receipts?.LEAN_OK;
  const leanOk = leanOkVal == null ? null : Boolean(Number(leanOkVal));
  const drift = typeof receipts?.drift_sha256 === "string" ? receipts.drift_sha256 : null;

  const vectorOk = inv?.vector_ok == null ? null : Boolean(inv.vector_ok);

  const templateBytes = Number(b?.template_bytes ?? 0);
  const deltaBytes = Number(b?.delta_bytes_total ?? 0);
  const wireTotal = Number(b?.wire_total_bytes ?? (templateBytes + deltaBytes));

  const ops_total = Number(b?.ops_total ?? (turns * muts));
  const bytes_per_op = Number(b?.bytes_per_op ?? (ops_total ? wireTotal / ops_total : 0));

  // seller framing
  const fanoutBytes = wireTotal * Math.max(0, Number(audience || 0));
  const estRevenue = Math.max(0, Number(audience || 0)) * Math.max(0, Number(price || 0));

  const curl = useMemo(() => {
    const bodyStr = JSON.stringify({ seed, n, turns, muts });
    return `curl -sS -X POST http://127.0.0.1:8787/api/wirepack/v45/run \\
  -H 'content-type: application/json' \\
  -d '${bodyStr}' | jq`;
  }, [seed, n, turns, muts]);

  async function copyCurl() {
    try {
      await navigator.clipboard.writeText(curl);
    } catch {
      // ignore
    }
  }

  const checks: Array<{ name: string; ok: boolean | null }> = [
    { name: "template_bytes_ok", ok: inv?.template_bytes_ok == null ? null : Boolean(inv.template_bytes_ok) },
    { name: "template_decode_ok", ok: inv?.template_decode_ok == null ? null : Boolean(inv.template_decode_ok) },
    { name: "delta_bytes_ok", ok: inv?.delta_bytes_ok == null ? null : Boolean(inv.delta_bytes_ok) },
    { name: "delta_decode_ok", ok: inv?.delta_decode_ok == null ? null : Boolean(inv.delta_decode_ok) },
    { name: "final_state_ok", ok: inv?.final_state_ok == null ? null : Boolean(inv.final_state_ok) },
  ];

  return (
    <div style={{ ...cardStyle(), padding: 14 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 900, color: "#111827" }}>
            v45 — Cross-language vectors <span style={{ fontSize: 11, fontWeight: 900, color: "#6b7280" }}>· seller-grade demo</span>
          </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 3, maxWidth: 860 }}>
            Same inputs → <b>byte-identical template + deltas</b> and the same <b>final_state_sha256</b> across implementations.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <Badge ok={vectorOk} label={`vector_ok: ${vectorOk === true ? "OK" : vectorOk === false ? "FAIL" : "—"}`} />
          <Badge ok={leanOk} label={`LEAN: ${leanOk === true ? "OK" : leanOk === false ? "FAIL" : "—"}`} />
          <button
            type="button"
            onClick={run}
            disabled={busy}
            style={{
              padding: "7px 12px",
              borderRadius: 999,
              border: "1px solid " + (busy ? "#e5e7eb" : "#111827"),
              background: busy ? "#f3f4f6" : "#111827",
              color: busy ? "#6b7280" : "#fff",
              fontSize: 11,
              fontWeight: 900,
              cursor: busy ? "not-allowed" : "pointer",
            }}
          >
            {busy ? "Running…" : "Run"}
          </button>
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

        <button type="button" onClick={copyCurl} style={pillStyle(false)} title="Copy a reproducible curl">
          Copy curl
        </button>

        <label style={{ display: "inline-flex", gap: 8, alignItems: "center", fontSize: 11, fontWeight: 900, color: "#111827" }}>
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
        {/* Seller panel */}
        <div style={{ ...cardStyle() }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>🎯 v45 — The “Polyglot Proof”</div>
            <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900 }}>cross-runtime byte identity</div>
          </div>

          <div style={{ marginTop: 8, ...miniText() }}>
            <b>The claim:</b> same inputs → Python + Node emit <b>byte-identical</b> template + deltas, and replay to the same{" "}
            <b>final_state_sha256</b>.
          </div>

          <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.55 }}>
            <div>
              <b>This run shape:</b> n=<b>{n.toLocaleString()}</b>, turns=<b>{turns.toLocaleString()}</b>, muts=
              <b>{muts.toLocaleString()}</b> → ops≈<b>{ops_total.toLocaleString()}</b>
            </div>

            <div style={{ marginTop: 8 }}>
              <b>What we compare:</b>
              <div style={{ marginTop: 4 }}>• template_bytes_ok — identical template bytes</div>
              <div>• delta_bytes_ok — identical delta stream bytes</div>
              <div>• template_decode_ok / delta_decode_ok — both decoders agree</div>
              <div>• final_state_ok — replay hash matches</div>
            </div>

            <div style={{ marginTop: 10, borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>Outputs you can pin (this run)</div>
              <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr", gap: 6, fontSize: 11, color: "#374151" }}>
                <div>
                  Template bytes: <b style={{ color: "#111827" }}>{bytes(templateBytes)}</b>
                </div>
                <div>
                  Delta bytes total: <b style={{ color: "#111827" }}>{bytes(deltaBytes)}</b>
                </div>
                <div>
                  Total wire: <b style={{ color: "#111827" }}>{bytes(wireTotal)}</b>{" "}
                  <span style={{ color: "#6b7280" }}>({bytes_per_op ? `${bytes_per_op.toFixed(2)} B/op` : "—"})</span>
                </div>

                <div>
                  Byte identity:{" "}
                  <b style={{ color: "#111827" }}>
                    {inv?.template_bytes_ok === true && inv?.delta_bytes_ok === true ? "PASS" : inv?.vector_ok === false ? "FAIL" : "—"}
                  </b>{" "}
                  <span style={{ color: "#6b7280" }}>(template + deltas match across runtimes)</span>
                </div>

                <div>
                  Replay identity:{" "}
                  <b style={{ color: "#111827" }}>
                    {inv?.final_state_ok === true ? "PASS" : inv?.vector_ok === false ? "FAIL" : "—"}
                  </b>{" "}
                  <span style={{ color: "#6b7280" }}>(final_state_sha256 matches)</span>
                </div>

                <div style={{ color: "#6b7280" }}>
                  drift_sha256: <code>{drift || "—"}</code>
                </div>
              </div>
            </div>

            <div style={{ marginTop: 10 }}>
              <b>Why it matters:</b> stable bytes remove the polyglot trust gap — generate receipts in one runtime and verify in another (and
              next: <b>Rust/WASM in-browser</b>).
            </div>
          </div>

          <div style={{ marginTop: 10, borderTop: "1px solid #f3f4f6", paddingTop: 10 }}>
            <div style={{ ...miniLabel() }}>Endpoint</div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              <code>POST /api/wirepack/v45/run</code>
            </div>
          </div>
        </div>

        {/* Main: controls + graph + outputs */}
        <div style={{ ...cardStyle() }}>
          {/* Controls */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 8 }}>
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
              n
              <input
                type="number"
                value={n}
                min={256}
                max={65536}
                onChange={(e) => setN(clamp(Number(e.target.value) || 256, 256, 65536))}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>
            <label style={{ fontSize: 11, color: "#374151" }}>
              turns
              <input
                type="number"
                value={turns}
                min={1}
                max={256}
                onChange={(e) => setTurns(clamp(Number(e.target.value) || 16, 1, 256))}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>
            <label style={{ fontSize: 11, color: "#374151" }}>
              muts
              <input
                type="number"
                value={muts}
                min={1}
                max={512}
                onChange={(e) => setMuts(clamp(Number(e.target.value) || 128, 1, 512))}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>
          </div>

          {/* Graph */}
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Polyglot identity graph</div>
              <div style={{ fontSize: 11, color: "#374151" }}>
                vector_ok: <b style={{ color: tri(vectorOk).color }}>{tri(vectorOk).label}</b>
                {"  "}· LEAN: <b style={{ color: tri(leanOk).color }}>{tri(leanOk).label}</b>
              </div>
            </div>

            <div style={{ marginTop: 10 }}>
              {out ? (
                <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", overflow: "hidden" }}>
                  {svgPolyglotGraph({
                    checks,
                    templateBytes,
                    deltaBytes,
                    n,
                    turns,
                    muts,
                    height: 220,
                  })}
                </div>
              ) : (
                <div
                  style={{
                    borderRadius: 16,
                    border: "1px dashed #e5e7eb",
                    background: "#f9fafb",
                    padding: 14,
                    fontSize: 11,
                    color: "#6b7280",
                  }}
                >
                  No output yet — hit <b>Run</b>.
                </div>
              )}
            </div>

            <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                <div style={{ ...miniLabel() }}>Transport footprint</div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                  total: <b style={{ color: "#111827" }}>{bytes(wireTotal)}</b>{" "}
                  <span style={{ color: "#6b7280" }}>
                    (template {bytes(templateBytes)} · deltas {bytes(deltaBytes)})
                  </span>
                </div>
              </div>
              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                <div style={{ ...miniLabel() }}>Wire efficiency</div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                  <b style={{ color: "#111827" }}>{bytes(wireTotal)}</b>{" "}
                  <span style={{ color: "#6b7280" }}>({bytes_per_op ? `${bytes_per_op.toFixed(2)} B/op` : "—"})</span>
                </div>
              </div>
              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                <div style={{ ...miniLabel() }}>Receipt</div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                  drift: <span style={{ color: "#6b7280" }}>{drift ? drift.slice(0, 10) + "…" : "—"}</span>
                </div>
              </div>
            </div>

            <div style={{ marginTop: 10, fontSize: 10, color: "#6b7280" }}>
              Bars are the five must-pass invariants. Footprint band shows how much of the transport is template vs deltas.
            </div>
          </div>

          {/* Output cards */}
          {out ? (
            <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: "#111827", display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                  Invariants
                  <Badge ok={vectorOk} label={`vector_ok: ${vectorOk === true ? "OK" : vectorOk === false ? "FAIL" : "—"}`} />
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
                  <div>
                    template_bytes_ok: <code>{String(inv.template_bytes_ok)}</code>
                  </div>
                  <div>
                    template_decode_ok: <code>{String(inv.template_decode_ok)}</code>
                  </div>
                  <div>
                    delta_bytes_ok: <code>{String(inv.delta_bytes_ok)}</code>
                  </div>
                  <div>
                    delta_decode_ok: <code>{String(inv.delta_decode_ok)}</code>
                  </div>
                  <div>
                    final_state_ok: <code>{String(inv.final_state_ok)}</code>
                  </div>

                  {out?.first_mismatch ? (
                    <div style={{ marginTop: 8, color: "#991b1b" }}>
                      first_mismatch: <code>{JSON.stringify(out.first_mismatch)}</code>
                    </div>
                  ) : null}
                </div>
              </div>

              <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: "#111827", display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                  Receipt
                  <Badge ok={leanOk} label={`LEAN_OK: ${leanOk === true ? "OK" : leanOk === false ? "FAIL" : "—"}`} />
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
                  <div style={{ color: "#6b7280" }}>
                    drift_sha256: <code>{drift || "—"}</code>
                  </div>
                  <div style={{ color: "#6b7280" }}>
                    final_state_sha256: <code>{String(out?.final_state_sha256 || "—")}</code>
                  </div>

                  <div style={{ marginTop: 10, fontWeight: 900, color: "#111827" }}>Bytes</div>
                  <div>
                    template_bytes: <b style={{ color: "#111827" }}>{bytes(templateBytes)}</b>{" "}
                    <span style={{ color: "#6b7280" }}>{b?.template_bytes != null ? `(${b.template_bytes} B)` : ""}</span>
                  </div>
                  <div>
                    delta_bytes_total: <b style={{ color: "#111827" }}>{bytes(deltaBytes)}</b>{" "}
                    <span style={{ color: "#6b7280" }}>{b?.delta_bytes_total != null ? `(${b.delta_bytes_total} B)` : ""}</span>
                  </div>
                  <div>
                    wire_total_bytes: <b style={{ color: "#111827" }}>{bytes(wireTotal)}</b>{" "}
                    <span style={{ color: "#6b7280" }}>{b?.wire_total_bytes != null ? `(${b.wire_total_bytes} B)` : ""}</span>
                  </div>
                  <div style={{ color: "#6b7280" }}>
                    receipts: <code>{JSON.stringify(receipts)}</code>
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {out && showRaw ? (
            <div style={{ marginTop: 12, borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Raw response</div>
              <pre style={{ marginTop: 8, fontSize: 11, color: "#111827", whiteSpace: "pre-wrap" }}>
                {JSON.stringify(out, null, 2)}
              </pre>
            </div>
          ) : null}
        </div>

        {/* What’s special explainer */}
        <div style={{ ...cardStyle() }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>What’s so special?</div>
            <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900 }}>why v45 matters</div>
          </div>

          <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>1) No polyglot trust gap</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                Different runtimes must agree on the <b>exact bytes</b>. If one language encodes “the same meaning” differently, receipts
                become non-portable.
              </div>
            </div>

            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>2) Five checks, one signal</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                <code>vector_ok</code> only passes when template + deltas are byte-identical, both decoders agree, and the final replay hash
                matches.
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                That’s why this demo is a “proof primitive”.
              </div>
            </div>

            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>3) Enables browser/WASM verification</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                Once bytes are stable, you can verify in any environment (Node, Python, Rust/WASM) and still get the same receipts and
                hashes.
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                <code>LEAN_OK</code> means invariants held end-to-end.
              </div>
            </div>

            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
              <div style={{ ...miniLabel() }}>Reproducible command</div>
              <pre style={{ marginTop: 8, fontSize: 10, color: "#111827", whiteSpace: "pre-wrap" }}>{curl}</pre>
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
          endpoint: <code>POST /api/wirepack/v45/run</code>
        </div>
        <div>
          wire: <b style={{ color: "#111827" }}>{bytes(wireTotal)}</b>{" "}
          <span style={{ color: "#6b7280" }}>
            · ops {ops_total.toLocaleString()} · bytes/op {bytes_per_op ? bytes_per_op.toFixed(2) : "—"}
          </span>
        </div>
      </div>
    </div>
  );
};