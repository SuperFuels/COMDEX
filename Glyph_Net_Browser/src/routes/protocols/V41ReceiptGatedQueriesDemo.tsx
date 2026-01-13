import React, { useMemo, useState } from "react";

/** ---------------- helpers (same “standard” as v32/v44) ---------------- */

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

function safeObj(x: any) {
  return x && typeof x === "object" ? x : {};
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

function StatTile(props: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
      <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900, letterSpacing: 0.3 }}>{props.label}</div>
      <div style={{ fontSize: 13, color: "#111827", fontWeight: 900, marginTop: 4 }}>{props.value}</div>
      {props.sub ? <div style={{ fontSize: 10, color: "#6b7280", marginTop: 4 }}>{props.sub}</div> : null}
    </div>
  );
}

async function fetchJson(url: string, body: any, timeoutMs = 12000) {
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

// Stable stringify: sort keys recursively (matches backend stableStringify)
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
  const data = new TextEncoder().encode(s);
  const digest = await crypto.subtle.digest("SHA-256", data);
  const u8 = new Uint8Array(digest);
  return Array.from(u8, (b) => b.toString(16).padStart(2, "0")).join("");
}

/** ---------------- tiny charts (no libs) ---------------- */

function GateTimelineChart(props: { steps: { label: string; ok: boolean | null }[] }) {
  const steps = props.steps ?? [];
  const w = 560;
  const h = 110;
  const pad = { l: 14, r: 14, t: 16, b: 18 };
  const innerW = w - pad.l - pad.r;

  const n = Math.max(1, steps.length);
  const stepW = innerW / n;

  const color = (ok: boolean | null) => (ok === null ? "#e5e7eb" : ok ? "#34d399" : "#f87171");
  const stroke = (ok: boolean | null) => (ok === null ? "#d1d5db" : ok ? "#10b981" : "#ef4444");

  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Gate pipeline</div>
        <div style={{ fontSize: 10, color: "#6b7280" }}>You don’t get results unless all checks pass</div>
      </div>

      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", marginTop: 8, display: "block" }}>
        {steps.map((s, i) => {
          const x = pad.l + i * stepW;
          const cx = x + stepW / 2;
          const cy = pad.t + 30;
          const ok = s.ok;
          return (
            <g key={i}>
              {i > 0 ? (
                <line
                  x1={pad.l + (i - 1) * stepW + stepW / 2}
                  y1={cy}
                  x2={cx}
                  y2={cy}
                  stroke="#e5e7eb"
                  strokeWidth={3}
                  strokeLinecap="round"
                />
              ) : null}
              <circle cx={cx} cy={cy} r={12} fill={color(ok)} stroke={stroke(ok)} strokeWidth={2} />
              <text x={cx} y={cy + 36} fontSize="10" textAnchor="middle" fill="#6b7280">
                {s.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function WorkVsLogChart(props: { fwStepsSum?: number | null; logN?: number | null }) {
  const fw = props.fwStepsSum ?? null;
  const ln = props.logN ?? null;

  const w = 560;
  const h = 160;
  const pad = { l: 70, r: 18, t: 18, b: 34 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;

  // draw two bars if present: fwStepsSum and logN (scaled independently but gives feel)
  const vals = [fw ?? 0, ln ?? 0];
  const max = Math.max(1, ...vals);

  const bars = [
    { label: "fw_steps_sum", v: fw ?? 0, fill: "#111827" },
    { label: "logN", v: ln ?? 0, fill: "#3b82f6" },
  ];
  const barW = innerW / bars.length;

  const y = (v: number) => pad.t + innerH * (1 - v / max);
  const bh = (v: number) => pad.t + innerH - y(v);

  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Work scaling signal</div>
        <div style={{ fontSize: 10, color: "#6b7280" }}>fw_steps_sum should track logN (not range length)</div>
      </div>

      {fw == null && ln == null ? (
        <div style={{ marginTop: 8, fontSize: 11, color: "#6b7280" }}>No work metrics returned yet.</div>
      ) : (
        <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", marginTop: 8, display: "block" }}>
          <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + innerH} stroke="#e5e7eb" />
          <line x1={pad.l} y1={pad.t + innerH} x2={pad.l + innerW} y2={pad.t + innerH} stroke="#e5e7eb" />
          {[0, max].map((t, i) => (
            <g key={i}>
              <line x1={pad.l - 4} y1={y(t)} x2={pad.l} y2={y(t)} stroke="#e5e7eb" />
              <text x={pad.l - 8} y={y(t) + 4} fontSize="10" textAnchor="end" fill="#6b7280">
                {t}
              </text>
            </g>
          ))}
          {bars.map((b, i) => {
            const x = pad.l + i * barW + Math.max(18, barW * 0.2);
            const bw = Math.max(120, barW * 0.6);
            const top = y(b.v);
            return (
              <g key={b.label}>
                <rect x={x} y={top} width={bw} height={bh(b.v)} rx={10} fill={b.fill} opacity={0.9} />
                <text x={x + bw / 2} y={top - 6} fontSize="10" textAnchor="middle" fill="#111827">
                  {b.v}
                </text>
                <text x={x + bw / 2} y={pad.t + innerH + 18} fontSize="10" textAnchor="middle" fill="#6b7280">
                  {b.label}
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}

function ChainList(props: { chain: { drift_sha256: string; prev: string }[] }) {
  const chain = props.chain ?? [];
  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Receipt chain (newest → oldest)</div>
      <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
        {chain.length === 0 ? (
          <div style={{ fontSize: 11, color: "#6b7280" }}>No chain yet — mint to create a leaf.</div>
        ) : (
          chain.slice(0, 12).map((x, i) => (
            <div
              key={i}
              style={{
                borderRadius: 12,
                border: "1px solid #e5e7eb",
                padding: 10,
                background: "#f9fafb",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                <div style={{ fontSize: 11, color: "#111827", fontWeight: 900 }}>
                  Leaf {i + 1}
                </div>
                <div style={{ fontSize: 10, color: "#6b7280" }}>
                  {i === 0 ? "active" : "ancestor"}
                </div>
              </div>
              <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
                drift_sha256: <code style={{ color: "#111827" }}>{x.drift_sha256}</code>
              </div>
              <div style={{ marginTop: 4, fontSize: 11, color: "#6b7280" }}>
                prev_drift_sha256: <code style={{ color: "#111827" }}>{x.prev || "—"}</code>
              </div>
            </div>
          ))
        )}
        {chain.length > 12 ? (
          <div style={{ fontSize: 11, color: "#6b7280" }}>… {chain.length - 12} more</div>
        ) : null}
      </div>
    </div>
  );
}

/** ---------------- v41 upgraded demo ---------------- */

export const V41ReceiptGatedQueriesDemo: React.FC = () => {
  const [seed, setSeed] = useState(1337);
  const [n, setN] = useState(4096);
  const [turns, setTurns] = useState(64);
  const [muts, setMuts] = useState(3);

  const [l, setL] = useState(0);
  const [r, setR] = useState(127);

  const [busyMint, setBusyMint] = useState(false);
  const [busyQuery, setBusyQuery] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [mintOut, setMintOut] = useState<any | null>(null);
  const [queryOut, setQueryOut] = useState<any | null>(null);

  // browser-side drift verification (null = not attempted yet)
  const [localVerified, setLocalVerified] = useState<null | boolean>(null);

  // UI extras
  const [showExamples, setShowExamples] = useState(true);
  const [receiptInput, setReceiptInput] = useState("");

  type ChainLink = { receipt: any; drift_sha256: string };

  // Chain is ordered leaf (newest) -> ... -> root (oldest)
  const [chain, setChain] = useState<ChainLink[]>([]);
  const prevDrift = chain[0]?.drift_sha256 || "";

  // Reset chain + outputs when core stream params change
  React.useEffect(() => {
    setChain([]);
    setMintOut(null);
    setQueryOut(null);
    setLocalVerified(null);
    setErr(null);
    setReceiptInput("");
  }, [seed, n, turns, muts]);

  const mintBody = useMemo(() => ({ seed, n, turns, muts, prev_drift_sha256: prevDrift }), [seed, n, turns, muts, prevDrift]);

  // ---- minted receipt fields (robust to small shape diffs)
  const leaf = chain[0] || null;
  const receipt = leaf?.receipt || mintOut?.receipt || mintOut?.receipts?.receipt || mintOut?.result?.receipt || null;

  const drift = leaf?.drift_sha256 || String(mintOut?.receipts?.drift_sha256 || mintOut?.drift_sha256 || "");

  const receipts = safeObj(mintOut?.receipts);
  const leafLeanOk =
    receipts?.LEAN_OK === 1 ||
    receipts?.LEAN_OK === true ||
    mintOut?.LEAN_OK === 1 ||
    mintOut?.LEAN_OK === true;

  // ---- query fields (robust to small shape diffs)
  const q = queryOut?.query || queryOut?.result || queryOut || {};
  const qInv = q?.invariants || queryOut?.invariants || null;
  const qBytes = safeObj(q?.bytes || queryOut?.bytes);

  const rangeOk: boolean | null = typeof qInv?.range_ok === "boolean" ? qInv.range_ok : null;

  const workLogOk: boolean | null =
    typeof qInv?.work_scales_with_logN === "boolean"
      ? qInv.work_scales_with_logN
      : typeof qInv?.work_scales_with_log_n === "boolean"
      ? qInv.work_scales_with_log_n
      : null;

  const queryRan = rangeOk !== null || workLogOk !== null;
  const queryOk = (rangeOk === null ? true : rangeOk) && (workLogOk === null ? true : workLogOk);

  // "receipt verified" = we have local drift verification + backend LEAN_OK at mint
  const receiptVerified = !!localVerified && !!leafLeanOk;

  // gate unlocked can be explicit, otherwise treat as unlocked if query ran
  const gateUnlocked =
    queryOut?.unlocked === true ||
    queryOut?.locked === false ||
    queryOut?.gate?.status === "UNLOCKED" ||
    queryRan;

  const leanVerified = receiptVerified && queryOk;

  const rangeLen = Math.max(0, r - l + 1);
  const opsTotal = Number(turns || 0) * Number(muts || 0);

  // Optional bytes (if backend returns them)
  const wireTotalBytes = Number(qBytes?.wire_total_bytes ?? qBytes?.wire_total ?? qBytes?.wire ?? 0) || null;

  // Optional work metrics
  const fwStepsSum: number | null = Number(qBytes?.fw_steps_sum ?? qBytes?.fw_steps_sum_total ?? qBytes?.fw_steps ?? NaN);
  const logN: number | null = Number(qBytes?.logN ?? qBytes?.log_n ?? qBytes?.logn ?? NaN);

  const fwStepsSumN = Number.isFinite(fwStepsSum) ? fwStepsSum : null;
  const logNN = Number.isFinite(logN) ? logN : null;

  const sumBaseline = q?.sum_baseline ?? queryOut?.sum_baseline ?? null;
  const sumStream = q?.sum_stream ?? queryOut?.sum_stream ?? null;

  const gateBadge = boolBadge(gateUnlocked ? true : (queryOut ? false : null));
  const receiptBadge = boolBadge(localVerified === null ? null : localVerified);
  const leanBadge = boolBadge(leanVerified ? true : (queryOut || mintOut ? false : null));

  const normalizedInput = receiptInput.trim().toLowerCase();
  const normalizedDrift = (drift || "").trim().toLowerCase();
  const inputMatchesCurrent = normalizedInput.length >= 8 && normalizedInput === normalizedDrift;
  const inputBadge = boolBadge(normalizedInput.length === 0 ? null : inputMatchesCurrent);

  const EXAMPLES = [
    { label: "Default (n=4096, range 0..127)", seed: 1337, n: 4096, turns: 64, muts: 3, l: 0, r: 127 },
    { label: "Tighter range (0..15)", seed: 1337, n: 4096, turns: 64, muts: 3, l: 0, r: 15 },
    { label: "Wider range (0..1023)", seed: 1337, n: 4096, turns: 64, muts: 3, l: 0, r: 1023 },
    { label: "Higher churn (turns=256)", seed: 2026, n: 4096, turns: 256, muts: 3, l: 0, r: 127 },
  ];

  async function mint() {
    if (busyMint) return;
    setBusyMint(true);
    setErr(null);
    setMintOut(null);
    setQueryOut(null);
    setLocalVerified(null);
    setReceiptInput("");

    try {
      const { ok, status, json } = await fetchJson("/api/wirepack/v41/mint", mintBody);
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setMintOut(json);

      const mintedDrift = String(json?.receipts?.drift_sha256 || json?.drift_sha256 || "");
      const mintedReceipt = json?.receipt ?? json?.receipts?.receipt ?? json?.result?.receipt;
      if (!mintedDrift || !mintedReceipt) throw new Error("Mint response missing receipt/drift.");

      // Local drift verification (browser-side)
      const want = await sha256HexUtf8(stableStringify(mintedReceipt));
      const okLocal = want === mintedDrift;
      setLocalVerified(okLocal);

      // Prepend new leaf (newest first)
      setChain((old) => [{ receipt: mintedReceipt, drift_sha256: mintedDrift }, ...old]);
    } catch (e: any) {
      setErr(e?.message || String(e));
    } finally {
      setBusyMint(false);
    }
  }

  async function runQuery() {
    if (busyQuery) return;
    setBusyQuery(true);
    setErr(null);
    setQueryOut(null);

    try {
      if (!chain.length) throw new Error("Missing receipt chain — mint first.");

      const { ok, status, json } = await fetchJson("/api/wirepack/v41/query", { chain, l, r }, 20000);
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setQueryOut(json);
    } catch (e: any) {
      setErr(e?.message || String(e));
    } finally {
      setBusyQuery(false);
    }
  }

  const chainViz = useMemo(() => {
    const xs = chain.map((x) => ({
      drift_sha256: String(x.drift_sha256 || ""),
      prev: String(x.receipt?.prev_drift_sha256 || ""),
    }));
    return xs;
  }, [chain]);

  const pipelineSteps = useMemo(
    () => [
      { label: "Mint", ok: mintOut ? true : null },
      { label: "Drift", ok: localVerified },
      { label: "LEAN", ok: mintOut ? !!leafLeanOk : null },
      { label: "Gate", ok: queryOut ? gateUnlocked : null },
      { label: "Query", ok: queryOut ? queryOk : null },
    ],
    [mintOut, localVerified, leafLeanOk, queryOut, gateUnlocked, queryOk]
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 900, color: "#111827" }}>v41 — Receipt-gated queries</div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            Queries are locked unless the receipt chain verifies (anti “demo theater”). Shows drift check + ancestry + unlock.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 10px",
              borderRadius: 999,
              border: `1px solid ${leanBadge.bd}`,
              background: leanBadge.bg,
              color: leanBadge.fg,
              fontSize: 11,
              fontWeight: 900,
              whiteSpace: "nowrap",
            }}
          >
            {leanVerified ? "LEAN VERIFIED" : "LEAN PENDING"}
          </div>

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
            onClick={mint}
            disabled={busyMint}
            style={{
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid " + (busyMint ? "#e5e7eb" : "#111827"),
              background: busyMint ? "#f9fafb" : "#111827",
              color: busyMint ? "#6b7280" : "#fff",
              fontSize: 11,
              fontWeight: 900,
              cursor: busyMint ? "not-allowed" : "pointer",
            }}
          >
            {busyMint ? "Minting…" : "Mint receipt"}
          </button>

          <button
            type="button"
            onClick={runQuery}
            disabled={busyQuery || !chain.length}
            style={{
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid " + (busyQuery || !chain.length ? "#e5e7eb" : "#111827"),
              background: busyQuery || !chain.length ? "#f9fafb" : "#111827",
              color: busyQuery || !chain.length ? "#6b7280" : "#fff",
              fontSize: 11,
              fontWeight: 900,
              cursor: busyQuery || !chain.length ? "not-allowed" : "pointer",
            }}
          >
            {busyQuery ? "Querying…" : "Run gated query"}
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
                onClick={() => {
                  setSeed(ex.seed);
                  setN(ex.n);
                  setTurns(ex.turns);
                  setMuts(ex.muts);
                  setL(ex.l);
                  setR(ex.r);
                }}
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

      {/* Params */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Parameters</div>
        <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "repeat(6, minmax(0, 1fr))", gap: 8 }}>
          {[
            { label: "seed", v: seed, set: setSeed, lo: 0, hi: 1_000_000 },
            { label: "n", v: n, set: setN, lo: 256, hi: 65536 },
            { label: "turns", v: turns, set: setTurns, lo: 1, hi: 4096 },
            { label: "muts", v: muts, set: setMuts, lo: 1, hi: 4096 },
            { label: "L", v: l, set: setL, lo: 0, hi: n - 1 },
            { label: "R", v: r, set: setR, lo: 0, hi: n - 1 },
          ].map((x) => (
            <label key={x.label} style={{ fontSize: 11, color: "#374151" }}>
              {x.label}
              <input
                type="number"
                value={x.v}
                min={x.lo}
                max={x.hi}
                onChange={(e) => x.set(clamp(Number(e.target.value) || 0, x.lo, x.hi))}
                style={{ width: "100%", marginTop: 6, padding: "8px 10px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>
          ))}
        </div>
        <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280" }}>
          ops_total (turns × muts): <b style={{ color: "#111827" }}>{opsTotal}</b> · range: <b style={{ color: "#111827" }}>[{l}..{r}]</b>{" "}
          · len: <b style={{ color: "#111827" }}>{rangeLen}</b>
        </div>
      </div>

      {err ? <div style={{ fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

      {/* Seller container (pitch) */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>
          🎯 v41 — The “trust unlock”: queries only execute when receipts verify
        </div>
        <div style={{ fontSize: 11, color: "#374151", marginTop: 8, lineHeight: 1.55 }}>
          <b>The claim:</b> You can’t get a query answer unless you present a valid receipt chain.
          <br />
          <br />
          <b>What’s enforced:</b>
          <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
            <li>
              <b>Determinism</b>: the receipt serializes stably and hashes to <code>drift_sha256</code>.
            </li>
            <li>
              <b>Ancestry</b>: each receipt points to <code>prev_drift_sha256</code> (no forked story).
            </li>
            <li>
              <b>Gating</b>: server stays <b>LOCKED</b> until chain verifies; only then it runs the query invariants.
            </li>
          </ul>
          <div style={{ marginTop: 10 }}>
            <b>Translation:</b> this kills “demo theater.” You can ship stream + receipts, and anyone can verify that the query answer was permitted and correct.
          </div>
        </div>
      </div>

      {/* Charts + stats */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: 10, alignItems: "start" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <GateTimelineChart steps={pipelineSteps} />
          <WorkVsLogChart fwStepsSum={fwStepsSumN} logN={logNN} />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <StatTile
            label="Gate"
            value={
              <span
                style={{
                  padding: "2px 8px",
                  borderRadius: 999,
                  border: `1px solid ${gateBadge.bd}`,
                  background: gateBadge.bg,
                  color: gateBadge.fg,
                  fontSize: 11,
                  fontWeight: 900,
                }}
              >
                {gateUnlocked ? "UNLOCKED" : (queryOut ? "LOCKED" : "—")}
              </span>
            }
            sub={queryOut?.reason ? <span style={{ color: "#991b1b" }}>{String(queryOut.reason)}</span> : "server state"}
          />
          <StatTile
            label="Local drift check"
            value={
              <span
                style={{
                  padding: "2px 8px",
                  borderRadius: 999,
                  border: `1px solid ${receiptBadge.bd}`,
                  background: receiptBadge.bg,
                  color: receiptBadge.fg,
                  fontSize: 11,
                  fontWeight: 900,
                }}
              >
                {receiptBadge.label}
              </span>
            }
            sub="browser recompute"
          />
          <StatTile
            label="Mint LEAN_OK"
            value={mintOut ? (leafLeanOk ? "1 ✅" : "0 ❌") : "—"}
            sub="backend check"
          />
          <StatTile
            label="Query invariants"
            value={
              <span
                style={{
                  padding: "2px 8px",
                  borderRadius: 999,
                  border: `1px solid ${boolBadge(queryOut ? queryOk : null).bd}`,
                  background: boolBadge(queryOut ? queryOk : null).bg,
                  color: boolBadge(queryOut ? queryOk : null).fg,
                  fontSize: 11,
                  fontWeight: 900,
                }}
              >
                {queryOut ? (queryOk ? "✅ OK" : "❌ FAIL") : "—"}
              </span>
            }
            sub="range_ok + work_logN"
          />
          <StatTile label="sum_baseline" value={sumBaseline ?? "—"} sub="reference" />
          <StatTile label="sum_stream" value={sumStream ?? "—"} sub="gated result" />
          <StatTile label="wire_total_bytes" value={wireTotalBytes ? bytes(wireTotalBytes) : "—"} sub={wireTotalBytes ? `${wireTotalBytes} B` : "optional"} />
          <StatTile label="range_len" value={qBytes?.range_len ?? rangeLen} sub="query span" />
        </div>
      </div>

      {/* Receipt verifier (input-driven like v44) */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Receipt verifier</div>
          <div
            style={{
              padding: "6px 10px",
              borderRadius: 999,
              border: `1px solid ${inputBadge.bd}`,
              background: inputBadge.bg,
              color: inputBadge.fg,
              fontSize: 11,
              fontWeight: 900,
            }}
          >
            {inputBadge.label}
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 10, alignItems: "center" }}>
          <input
            value={receiptInput}
            onChange={(e) => setReceiptInput(e.target.value)}
            placeholder="Paste drift_sha256 here to compare against current leaf…"
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
          >
            Use current drift
          </button>
        </div>

        <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280", lineHeight: 1.55 }}>
          <div>
            current drift_sha256: <code style={{ color: "#111827" }}>{drift || "—"}</code>
          </div>
          <div style={{ marginTop: 4 }}>
            Note: this input compare is just a UX helper; the real proof is the browser-side recompute (Local drift check) + backend LEAN_OK.
          </div>
        </div>
      </div>

      {/* Chain + Receipt + Query details */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, alignItems: "start" }}>
        <ChainList chain={chainViz} />

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Current leaf receipt</div>
            <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
              <div>drift_sha256: <code>{drift || "—"}</code></div>
              <div>final_state_sha256: <code>{String(receipt?.final_state_sha256 || "—")}</code></div>
              <div>prev_drift_sha256: <code>{String(receipt?.prev_drift_sha256 || "—")}</code></div>
              <div>LEAN_OK: <code>{mintOut ? (leafLeanOk ? "1" : "0") : "—"}</code></div>
            </div>
          </div>

          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Query invariants</div>
            <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
              <div>range_ok: <code>{rangeOk === null ? "—" : String(rangeOk)}</code></div>
              <div>work_scales_with_logN: <code>{workLogOk === null ? "—" : String(workLogOk)}</code></div>
              <div>sum_baseline: <code>{String(sumBaseline ?? "—")}</code></div>
              <div>sum_stream: <code>{String(sumStream ?? "—")}</code></div>
              <div style={{ paddingTop: 8, borderTop: "1px solid #e5e7eb", marginTop: 8 }}>
                ops_total: <code>{qBytes?.ops_total ?? opsTotal ?? "—"}</code>
              </div>
              <div>range_len: <code>{qBytes?.range_len ?? rangeLen}</code></div>
              <div>fw_steps_sum: <code>{qBytes?.fw_steps_sum ?? "—"}</code> / logN <code>{qBytes?.logN ?? "—"}</code></div>
            </div>
          </div>
        </div>

        {/* Raw */}
        <div style={{ gridColumn: "1 / -1", borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Raw responses</div>
          <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>mint</div>
              <pre style={{ marginTop: 8, fontSize: 11, color: "#111827", whiteSpace: "pre-wrap" }}>
                {mintOut ? JSON.stringify(mintOut, null, 2) : "—"}
              </pre>
            </div>
            <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>query</div>
              <pre style={{ marginTop: 8, fontSize: 11, color: "#111827", whiteSpace: "pre-wrap" }}>
                {queryOut ? JSON.stringify(queryOut, null, 2) : "—"}
              </pre>
            </div>
          </div>
        </div>
      </div>

      {/* Endpoint footer */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10, fontSize: 11, color: "#6b7280" }}>
        Endpoints:
        <div style={{ marginTop: 6 }}>
          <code>POST /api/wirepack/v41/mint</code> · <code>POST /api/wirepack/v41/query</code>
        </div>
      </div>
    </div>
  );
};