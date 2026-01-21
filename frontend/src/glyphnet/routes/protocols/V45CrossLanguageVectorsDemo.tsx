"use client";

import React, { useMemo, useState } from "react";

/** ---------------- helpers ---------------- */

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

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function tri(ok: boolean | null) {
  if (ok === null) return { label: "—", cls: "border-slate-200 bg-slate-50 text-slate-500", icon: "•" };
  return ok
    ? { label: "OK", cls: "border-emerald-200 bg-emerald-50 text-emerald-800", icon: "✅" }
    : { label: "FAIL", cls: "border-red-200 bg-red-50 text-red-800", icon: "⚠️" };
}

/** ---------------- branded atoms (SLE/RQC light) ---------------- */

function Card(props: { title?: string; subtitle?: React.ReactNode; right?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <div className={["rounded-2xl border border-slate-200 bg-white p-4 shadow-sm", props.className || ""].join(" ")}>
      {(props.title || props.right) && (
        <div className="flex items-start justify-between gap-4">
          <div>
            {props.title ? <div className="text-sm font-extrabold tracking-tight text-slate-900">{props.title}</div> : null}
            {props.subtitle ? <div className="mt-1 text-xs font-medium text-slate-500">{props.subtitle}</div> : null}
          </div>
          {props.right ? <div className="shrink-0">{props.right}</div> : null}
        </div>
      )}
      <div className={(props.title || props.right) ? "mt-3" : ""}>{props.children}</div>
    </div>
  );
}

function StatTile(props: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{props.label}</div>
      <div className="mt-1 text-sm font-extrabold text-slate-900">{props.value}</div>
      {props.sub ? <div className="mt-1 text-[11px] text-slate-500">{props.sub}</div> : null}
    </div>
  );
}

function PillButton(props: {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "ghost" | "primary";
  title?: string;
}) {
  const v = props.variant || "ghost";
  const base =
    "px-4 py-2 rounded-full text-xs font-semibold border transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1B74E4]/30";
  const ghost = "border-slate-200 bg-white text-slate-800 hover:bg-slate-50";
  const primary = "border-[#1B74E4] bg-[#1B74E4] text-white hover:brightness-110";
  const disabled = "opacity-60 cursor-default hover:brightness-100";

  return (
    <button
      type="button"
      onClick={props.onClick}
      disabled={props.disabled}
      title={props.title}
      className={[base, v === "primary" ? primary : ghost, props.disabled ? disabled : ""].join(" ")}
    >
      {props.children}
    </button>
  );
}

function Badge(props: { ok: boolean | null; label: string }) {
  const t = tri(props.ok);
  return (
    <span className={`px-3 py-1 rounded-full border text-xs font-extrabold inline-flex items-center gap-2 whitespace-nowrap ${t.cls}`}>
      <span className="text-[12px]">{t.icon}</span>
      {props.label}
    </span>
  );
}

/** ---------------- v45 graph ---------------- */
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
  const barH = Math.max(16, Math.round(plotH * 0.1));
  const barGap = 10;

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
      <rect x={x0} y={y0} width={plotW} height={plotH} rx={12} ry={12} fill="transparent" stroke="#e2e8f0" />

      <text x={x0} y={headerY} fontSize={11} fill="#64748b">
        Byte identity checklist (Python ↔ Node) + footprint (template vs deltas)
      </text>

      {checks.map((c, i) => {
        const y = barsTop + i * (barH + barGap);
        const t = tri(c.ok);
        // light band behind each row
        const fill = c.ok === true ? "#ecfdf5" : c.ok === false ? "#fef2f2" : "#f8fafc";
        const stroke = c.ok === true ? "#a7f3d0" : c.ok === false ? "#fecaca" : "#e2e8f0";
        const color = c.ok === true ? "#065f46" : c.ok === false ? "#991b1b" : "#64748b";
        return (
          <g key={c.name}>
            <rect x={x0} y={y} width={plotW} height={barH} rx={12} ry={12} fill="#f8fafc" stroke="#e2e8f0" />
            <rect x={x0} y={y} width={plotW} height={barH} rx={12} ry={12} fill={fill} stroke={stroke} />
            <text x={x0 + 10} y={y + barH / 2 + 4} fontSize={11} fill={color}>
              {t.icon} {c.name}
            </text>
            <text x={x0 + plotW - 10} y={y + barH / 2 + 4} fontSize={11} fill={color} textAnchor="end">
              {t.label}
            </text>
          </g>
        );
      })}

      <text x={x0} y={footprintY - 6} fontSize={11} fill="#64748b">
        Footprint split: template bytes vs delta bytes (total transport)
      </text>
      <rect x={x0} y={footprintY} width={plotW} height={footprintH} rx={12} ry={12} fill="#f8fafc" stroke="#e2e8f0" />
      {/* template */}
      <rect x={x0} y={footprintY} width={Math.max(2, tW)} height={footprintH} rx={12} ry={12} fill="#dbeafe" stroke="#93c5fd" />
      {/* deltas */}
      <rect
        x={x0 + Math.max(2, tW)}
        y={footprintY}
        width={Math.max(2, dW)}
        height={footprintH}
        rx={12}
        ry={12}
        fill="#cffafe"
        stroke="#67e8f9"
      />

      <text x={x0} y={footprintY + footprintH + 14} fontSize={11} fill="#64748b">
        n={n.toLocaleString()} · turns={turns.toLocaleString()} · muts={muts.toLocaleString()}
      </text>
      <text x={x0 + plotW} y={footprintY + footprintH + 14} fontSize={11} fill="#64748b" textAnchor="end">
        template={bytes(templateBytes)} · deltas={bytes(deltaBytes)} · total={bytes(total)}
      </text>
    </svg>
  );
}

/** ---------------- demo ---------------- */

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

  const nodeOk = inv?.node_ok == null ? null : Boolean(inv.node_ok);

  const vectorOkRaw = inv?.vector_ok == null ? null : Boolean(inv.vector_ok);
  // If Node verifier isn’t configured, show pending instead of FAIL.
  const vectorOk = nodeOk === null ? null : vectorOkRaw;

  const leanOkVal = receipts?.LEAN_OK;
  const leanOkRaw = leanOkVal == null ? null : Boolean(Number(leanOkVal));
  // Same rule: if Node verifier isn’t configured, don’t show LEAN FAIL.
  const leanOk = nodeOk === null ? null : leanOkRaw;

  const drift = typeof receipts?.drift_sha256 === "string" ? receipts.drift_sha256 : null;

  const templateBytes = Number(b?.template_bytes ?? 0);
  const deltaBytes = Number(b?.delta_bytes_total ?? 0);
  const wireTotal = Number(b?.wire_total_bytes ?? templateBytes + deltaBytes);

  const ops_total = Number(b?.ops_total ?? turns * muts);
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
    { name: "node_ok", ok: inv?.node_ok == null ? null : Boolean(inv.node_ok) },
  ];

  return (
    <div className="rounded-[2.5rem] border border-slate-200 bg-[#F8FAFC] p-6 shadow-xl">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-widest text-slate-400">WirePack / Trust</div>
          <div className="mt-1 text-base font-black tracking-tight text-slate-900">
            v45 — Cross-language vectors{" "}
            <span className="text-xs font-extrabold text-slate-500">· polyglot byte identity</span>
          </div>
          <div className="mt-1 text-xs text-slate-600 max-w-[860px]">
            Same inputs → <span className="font-semibold text-slate-900">byte-identical template + deltas</span> and the same{" "}
            <span className="font-semibold text-slate-900">final_state_sha256</span> across implementations.
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge ok={vectorOk} label={`vector_ok: ${vectorOk === true ? "OK" : vectorOk === false ? "FAIL" : "—"}`} />
          <Badge ok={leanOk} label={`LEAN: ${leanOk === true ? "OK" : leanOk === false ? "FAIL" : "—"}`} />
          <PillButton onClick={run} disabled={busy} variant="primary">
            {busy ? "Running…" : "Run"}
          </PillButton>
        </div>
      </div>

      {/* Presets + quick actions */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400">Presets</span>
        <PillButton onClick={() => applyPreset("balanced")}>Balanced</PillButton>
        <PillButton onClick={() => applyPreset("stress")}>Stress</PillButton>
        <PillButton onClick={() => applyPreset("tiny")}>Tiny</PillButton>

        <span className="mx-2 h-5 w-px bg-slate-200" />

        <PillButton onClick={copyCurl} title="Copy a reproducible curl">
          Copy curl
        </PillButton>

        <label className="ml-2 inline-flex items-center gap-2 text-xs font-extrabold text-slate-800">
          <input type="checkbox" checked={showRaw} onChange={(e) => setShowRaw(e.target.checked)} />
          Raw JSON
        </label>
      </div>

      {err ? <div className="mt-3 text-xs font-semibold text-red-700">{err}</div> : null}

      {/* 3-column layout */}
      <div className="mt-4 grid gap-3 xl:grid-cols-[minmax(260px,320px)_minmax(420px,1fr)_minmax(260px,340px)] items-start">
        {/* Seller panel */}
        <Card
          title="🎯 v45 — The “Polyglot Proof”"
          subtitle={<span className="text-slate-500">cross-runtime byte identity</span>}
        >
          <div className="text-xs text-slate-700 leading-relaxed">
            <div>
              <span className="font-semibold">The claim:</span> same inputs → Python + Node emit{" "}
              <span className="font-semibold text-slate-900">byte-identical</span> template + deltas, and replay to the same{" "}
              <span className="font-semibold text-slate-900">final_state_sha256</span>.
            </div>

            <div className="mt-3">
              <span className="font-semibold">This run shape:</span> n=<span className="font-semibold text-slate-900">{n.toLocaleString()}</span>
              , turns=<span className="font-semibold text-slate-900">{turns.toLocaleString()}</span>, muts=
              <span className="font-semibold text-slate-900">{muts.toLocaleString()}</span> → ops≈
              <span className="font-semibold text-slate-900">{ops_total.toLocaleString()}</span>
            </div>

            <div className="mt-3">
              <span className="font-semibold">What we compare:</span>
              <div className="mt-1 text-slate-600">
                • template_bytes_ok — identical template bytes
                <br />• delta_bytes_ok — identical delta stream bytes
                <br />• template_decode_ok / delta_decode_ok — both decoders agree
                <br />• final_state_ok — replay hash matches
              </div>
            </div>

            <div className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 p-3">
              <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Outputs you can pin (this run)</div>
              <div className="mt-2 grid gap-1 text-xs text-slate-700">
                <div>
                  Template bytes: <span className="font-extrabold text-slate-900">{bytes(templateBytes)}</span>
                </div>
                <div>
                  Delta bytes total: <span className="font-extrabold text-slate-900">{bytes(deltaBytes)}</span>
                </div>
                <div>
                  Total wire: <span className="font-extrabold text-slate-900">{bytes(wireTotal)}</span>{" "}
                  <span className="text-slate-500">({bytes_per_op ? `${bytes_per_op.toFixed(2)} B/op` : "—"})</span>
                </div>
                <div>
                  Byte identity:{" "}
                  <span className="font-extrabold text-slate-900">
                    {inv?.template_bytes_ok === true && inv?.delta_bytes_ok === true ? "PASS" : inv?.vector_ok === false ? "FAIL" : "—"}
                  </span>{" "}
                  <span className="text-slate-500">(template + deltas match)</span>
                </div>
                <div>
                  Replay identity:{" "}
                  <span className="font-extrabold text-slate-900">
                    {inv?.final_state_ok === true ? "PASS" : inv?.vector_ok === false ? "FAIL" : "—"}
                  </span>{" "}
                  <span className="text-slate-500">(final_state_sha256 matches)</span>
                </div>
                <div className="text-slate-500">
                  drift_sha256: <code className="text-slate-900">{drift || "—"}</code>
                </div>
              </div>
            </div>

            <div className="mt-3">
              <span className="font-semibold">Why it matters:</span> stable bytes remove the polyglot trust gap — receipts in one runtime,
              verified in another (next: <span className="font-semibold text-slate-900">Rust/WASM in-browser</span>).
            </div>

            <div className="mt-4 border-t border-slate-200 pt-3 text-xs text-slate-500">
              Endpoint: <code className="text-slate-900">POST /api/wirepack/v45/run</code>
            </div>
          </div>
        </Card>

        {/* Main: controls + graph + outputs */}
        <Card title="Polyglot identity graph" subtitle="five invariants + footprint split (template vs deltas)">
          {/* Controls */}
          <div className="grid gap-2 md:grid-cols-4">
            {[
              ["seed", seed, (v: number) => setSeed(v || 0), 0, 1_000_000],
              ["n", n, (v: number) => setN(clamp(v || 256, 256, 65536)), 256, 65536],
              ["turns", turns, (v: number) => setTurns(clamp(v || 16, 1, 256)), 1, 256],
              ["muts", muts, (v: number) => setMuts(clamp(v || 128, 1, 512)), 1, 512],
            ].map(([label, val, setVal, lo, hi]: any) => (
              <label key={label} className="text-xs font-semibold text-slate-600">
                {label}
                <input
                  type="number"
                  value={val}
                  min={lo}
                  max={hi}
                  onChange={(e) => setVal(Number(e.target.value))}
                  className="mt-1 w-full px-3 py-2 rounded-xl border border-slate-200 bg-white text-slate-900 text-xs font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1B74E4]/30"
                />
              </label>
            ))}
          </div>

          {/* Graph */}
          <div className="mt-4">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <div className="text-sm font-extrabold text-slate-900">Graph</div>
              <div className="text-xs text-slate-600">
                vector_ok: <span className={`font-extrabold ${vectorOk === true ? "text-emerald-700" : vectorOk === false ? "text-red-700" : "text-slate-500"}`}>{tri(vectorOk).label}</span>
                {" · "}
                LEAN: <span className={`font-extrabold ${leanOk === true ? "text-emerald-700" : leanOk === false ? "text-red-700" : "text-slate-500"}`}>{tri(leanOk).label}</span>
              </div>
            </div>

            <div className="mt-3">
              {out ? (
                <div className="rounded-2xl border border-slate-200 overflow-hidden bg-white">
                  {svgPolyglotGraph({ checks, templateBytes, deltaBytes, n, turns, muts, height: 220 })}
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-xs text-slate-500">
                  No output yet — hit <span className="font-semibold text-slate-900">Run</span>.
                </div>
              )}
            </div>

            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <StatTile
                label="Transport footprint"
                value={<span>{bytes(wireTotal)}</span>}
                sub={
                  <span>
                    template {bytes(templateBytes)} · deltas {bytes(deltaBytes)}
                  </span>
                }
              />
              <StatTile
                label="Wire efficiency"
                value={<span>{bytes(wireTotal)}</span>}
                sub={<span>{bytes_per_op ? `${bytes_per_op.toFixed(2)} B/op` : "—"}</span>}
              />
              <StatTile
                label="Receipt"
                value={<span className="font-mono text-xs">{drift ? drift.slice(0, 10) + "…" : "—"}</span>}
                sub={<span>drift_sha256</span>}
              />
            </div>

            <div className="mt-3 text-[11px] text-slate-500">
              Bars are the five must-pass invariants. Footprint band shows how much of the transport is template vs deltas.
            </div>
          </div>

          {/* Output cards */}
          {out ? (
            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              <Card
                title="Invariants"
                right={<Badge ok={vectorOk} label={`vector_ok: ${vectorOk === true ? "OK" : vectorOk === false ? "FAIL" : "—"}`} />}
              >
                <div className="text-xs text-slate-700 leading-relaxed">
                  <div>
                    node_ok: <code className="text-slate-900">{String(inv.node_ok)}</code>
                  </div>
                  <div>
                    template_bytes_ok: <code className="text-slate-900">{String(inv.template_bytes_ok)}</code>
                  </div>
                  <div>
                    template_decode_ok: <code className="text-slate-900">{String(inv.template_decode_ok)}</code>
                  </div>
                  <div>
                    delta_bytes_ok: <code className="text-slate-900">{String(inv.delta_bytes_ok)}</code>
                  </div>
                  <div>
                    delta_decode_ok: <code className="text-slate-900">{String(inv.delta_decode_ok)}</code>
                  </div>
                  <div>
                    final_state_ok: <code className="text-slate-900">{String(inv.final_state_ok)}</code>
                  </div>

                  {out?.first_mismatch ? (
                    <div className="mt-2 text-red-700">
                      first_mismatch: <code className="text-slate-900">{JSON.stringify(out.first_mismatch)}</code>
                    </div>
                  ) : null}
                </div>
              </Card>

              <Card
                title="Receipt"
                right={<Badge ok={leanOk} label={`LEAN_OK: ${leanOk === true ? "OK" : leanOk === false ? "FAIL" : "—"}`} />}
              >
                <div className="text-xs text-slate-700 leading-relaxed">
                  <div className="text-slate-500">
                    drift_sha256: <code className="text-slate-900">{drift || "—"}</code>
                  </div>
                  <div className="text-slate-500">
                    final_state_sha256: <code className="text-slate-900">{String(out?.final_state_sha256 || "—")}</code>
                  </div>

                  <div className="mt-3 text-xs font-extrabold text-slate-900">Bytes</div>
                  <div>
                    template_bytes: <span className="font-extrabold text-slate-900">{bytes(templateBytes)}</span>{" "}
                    <span className="text-slate-500">{b?.template_bytes != null ? `(${b.template_bytes} B)` : ""}</span>
                  </div>
                  <div>
                    delta_bytes_total: <span className="font-extrabold text-slate-900">{bytes(deltaBytes)}</span>{" "}
                    <span className="text-slate-500">{b?.delta_bytes_total != null ? `(${b.delta_bytes_total} B)` : ""}</span>
                  </div>
                  <div>
                    wire_total_bytes: <span className="font-extrabold text-slate-900">{bytes(wireTotal)}</span>{" "}
                    <span className="text-slate-500">{b?.wire_total_bytes != null ? `(${b.wire_total_bytes} B)` : ""}</span>
                  </div>

                  <div className="mt-2 text-slate-500">
                    receipts: <code className="text-slate-900">{JSON.stringify(receipts)}</code>
                  </div>
                </div>
              </Card>
            </div>
          ) : null}

          {out && showRaw ? (
            <Card title="Raw response" className="mt-4">
              <pre className="mt-1 text-xs text-slate-900 whitespace-pre-wrap">{JSON.stringify(out, null, 2)}</pre>
            </Card>
          ) : null}
        </Card>

        {/* What’s special explainer */}
        <Card title="What’s so special?" subtitle="why v45 matters">
          <div className="grid gap-3">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
              <div className="text-[11px] font-extrabold text-slate-900">1) No polyglot trust gap</div>
              <div className="mt-2 text-xs text-slate-700 leading-relaxed">
                Different runtimes must agree on the <span className="font-semibold">exact bytes</span>. If one language encodes “the same
                meaning” differently, receipts become non-portable.
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
              <div className="text-[11px] font-extrabold text-slate-900">2) Five checks, one signal</div>
              <div className="mt-2 text-xs text-slate-700 leading-relaxed">
                <code className="text-slate-900">vector_ok</code> only passes when template + deltas are byte-identical, both decoders agree,
                and the final replay hash matches. That’s why this demo is a “proof primitive”.
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
              <div className="text-[11px] font-extrabold text-slate-900">3) Enables browser/WASM verification</div>
              <div className="mt-2 text-xs text-slate-700 leading-relaxed">
                Once bytes are stable, you can verify in any environment (Node, Python, Rust/WASM) and still get the same receipts and hashes.
                <div className="mt-2">
                  <code className="text-slate-900">LEAN_OK</code> means invariants held end-to-end.
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-3">
              <div className="text-[11px] font-extrabold text-slate-900">Reproducible command</div>
              <pre className="mt-2 text-[11px] text-slate-900 whitespace-pre-wrap">{curl}</pre>
              <div className="mt-2 text-[11px] text-slate-500">
                seller: <span className="font-semibold text-slate-900">{sellerName}</span> · sku{" "}
                <span className="font-semibold text-slate-900">{sku}</span>
              </div>
              <div className="mt-1 text-[11px] text-slate-500">
                audience <span className="font-semibold text-slate-900">{Number(audience || 0).toLocaleString()}</span> → fanout{" "}
                <span className="font-semibold text-slate-900">{bytes(fanoutBytes)}</span> · est revenue{" "}
                <span className="font-semibold text-slate-900">{estRevenue.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Footer */}
      <div className="mt-4 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600 flex flex-wrap items-center justify-between gap-2">
        <div>
          endpoint: <code className="text-slate-900">POST /api/wirepack/v45/run</code>
        </div>
        <div>
          wire: <span className="font-extrabold text-slate-900">{bytes(wireTotal)}</span>{" "}
          <span className="text-slate-500">
            · ops {ops_total.toLocaleString()} · bytes/op {bytes_per_op ? bytes_per_op.toFixed(2) : "—"}
          </span>
        </div>
      </div>
    </div>
  );
};