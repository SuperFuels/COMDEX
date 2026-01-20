"use client";

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
  return x && typeof x !== "object" ? {} : x && typeof x === "object" ? x : {};
}

function boolBadge(ok: boolean | null) {
  const good = ok === true;
  const bad = ok === false;
  const bg = good ? "#ecfdf5" : bad ? "#fef2f2" : "#f8fafc";
  const fg = good ? "#065f46" : bad ? "#991b1b" : "#64748b";
  const bd = good ? "#a7f3d0" : bad ? "#fecaca" : "#e2e8f0";
  const label = good ? "✅ VERIFIED" : bad ? "❌ FAIL" : "—";
  return { bg, fg, bd, label };
}

/** ---------------- branded atoms (SLE/RQC light) ---------------- */

function StatTile(props: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{props.label}</div>
      <div className="mt-1 text-sm font-extrabold text-slate-900">{props.value}</div>
      {props.sub ? <div className="mt-1 text-[11px] text-slate-500">{props.sub}</div> : null}
    </div>
  );
}

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
  const disabled = "opacity-60 cursor-not-allowed hover:brightness-100";

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

  // light theme mapping
  const color = (ok: boolean | null) => (ok === null ? "#e2e8f0" : ok ? "#34d399" : "#f87171");
  const stroke = (ok: boolean | null) => (ok === null ? "#cbd5e1" : ok ? "#10b981" : "#ef4444");

  return (
    <Card title="Gate pipeline" subtitle="You don’t get results unless all checks pass">
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
                  stroke="#e2e8f0"
                  strokeWidth={3}
                  strokeLinecap="round"
                />
              ) : null}
              <circle cx={cx} cy={cy} r={12} fill={color(ok)} stroke={stroke(ok)} strokeWidth={2} />
              <text x={cx} y={cy + 36} fontSize="10" textAnchor="middle" fill="#64748b">
                {s.label}
              </text>
            </g>
          );
        })}
      </svg>
    </Card>
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

  const vals = [fw ?? 0, ln ?? 0];
  const max = Math.max(1, ...vals);

  const bars = [
    { label: "fw_steps_sum", v: fw ?? 0, fill: "#0f172a" }, // slate-900-ish
    { label: "logN", v: ln ?? 0, fill: "#1B74E4" }, // brand primary
  ];
  const barW = innerW / bars.length;

  const y = (v: number) => pad.t + innerH * (1 - v / max);
  const bh = (v: number) => pad.t + innerH - y(v);

  return (
    <Card title="Work scaling signal" subtitle="fw_steps_sum should track logN (not range length)">
      {fw == null && ln == null ? (
        <div className="mt-2 text-xs text-slate-500">No work metrics returned yet.</div>
      ) : (
        <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", marginTop: 8, display: "block" }}>
          <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + innerH} stroke="#e2e8f0" />
          <line x1={pad.l} y1={pad.t + innerH} x2={pad.l + innerW} y2={pad.t + innerH} stroke="#e2e8f0" />
          {[0, max].map((t, i) => (
            <g key={i}>
              <line x1={pad.l - 4} y1={y(t)} x2={pad.l} y2={y(t)} stroke="#e2e8f0" />
              <text x={pad.l - 8} y={y(t) + 4} fontSize="10" textAnchor="end" fill="#64748b">
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
                <text x={x + bw / 2} y={top - 6} fontSize="10" textAnchor="middle" fill="#0f172a">
                  {b.v}
                </text>
                <text x={x + bw / 2} y={pad.t + innerH + 18} fontSize="10" textAnchor="middle" fill="#64748b">
                  {b.label}
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </Card>
  );
}

function ChainList(props: { chain: { drift_sha256: string; prev: string }[] }) {
  const chain = props.chain ?? [];
  return (
    <Card title="Receipt chain" subtitle="newest → oldest">
      <div className="mt-2 flex flex-col gap-2">
        {chain.length === 0 ? (
          <div className="text-xs text-slate-500">No chain yet — mint to create a leaf.</div>
        ) : (
          chain.slice(0, 12).map((x, i) => (
            <div key={i} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-xs font-extrabold text-slate-900">Leaf {i + 1}</div>
                <div className="text-[11px] font-semibold text-slate-500">{i === 0 ? "active" : "ancestor"}</div>
              </div>
              <div className="mt-2 text-xs text-slate-500">
                drift_sha256: <code className="text-slate-900">{x.drift_sha256}</code>
              </div>
              <div className="mt-1 text-xs text-slate-500">
                prev_drift_sha256: <code className="text-slate-900">{x.prev || "—"}</code>
              </div>
            </div>
          ))
        )}
        {chain.length > 12 ? <div className="text-xs text-slate-500">… {chain.length - 12} more</div> : null}
      </div>
    </Card>
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
    receipts?.LEAN_OK === 1 || receipts?.LEAN_OK === true || mintOut?.LEAN_OK === 1 || mintOut?.LEAN_OK === true;

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
  const gateUnlocked = queryOut?.unlocked === true || queryOut?.locked === false || queryOut?.gate?.status === "UNLOCKED" || queryRan;

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

  const gateBadge = boolBadge(gateUnlocked ? true : queryOut ? false : null);
  const receiptBadge = boolBadge(localVerified === null ? null : localVerified);
  const leanBadge = boolBadge(leanVerified ? true : queryOut || mintOut ? false : null);

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
    <div className="rounded-[2.5rem] border border-slate-200 bg-[#F8FAFC] p-6 shadow-xl">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-widest text-slate-400">WirePack / Trust</div>
          <div className="mt-1 text-base font-black tracking-tight text-slate-900">v41 — Receipt-gated queries</div>
          <div className="mt-1 text-xs text-slate-600 max-w-[860px]">
            Queries are locked unless the receipt chain verifies (anti “demo theater”). Shows drift check + ancestry + unlock.
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span
            className={[
              "px-3 py-1 rounded-full border text-xs font-extrabold whitespace-nowrap",
              leanVerified ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-slate-200 bg-white text-slate-700",
            ].join(" ")}
          >
            {leanVerified ? "LEAN VERIFIED" : "LEAN PENDING"}
          </span>

          <PillButton onClick={() => setShowExamples((s) => !s)}>Examples</PillButton>
          <PillButton onClick={mint} disabled={busyMint} variant="primary">
            {busyMint ? "Minting…" : "Mint receipt"}
          </PillButton>
          <PillButton onClick={runQuery} disabled={busyQuery || !chain.length} variant="primary">
            {busyQuery ? "Querying…" : "Run gated query"}
          </PillButton>
        </div>
      </div>

      {showExamples ? (
        <Card title="Presets">
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <PillButton
                key={ex.label}
                onClick={() => {
                  setSeed(ex.seed);
                  setN(ex.n);
                  setTurns(ex.turns);
                  setMuts(ex.muts);
                  setL(ex.l);
                  setR(ex.r);
                }}
              >
                {ex.label}
              </PillButton>
            ))}
          </div>
        </Card>
      ) : null}

      {/* Params */}
      <Card title="Parameters">
        <div className="grid gap-2 md:grid-cols-6">
          {[
            { label: "seed", v: seed, set: setSeed, lo: 0, hi: 1_000_000 },
            { label: "n", v: n, set: setN, lo: 256, hi: 65536 },
            { label: "turns", v: turns, set: setTurns, lo: 1, hi: 4096 },
            { label: "muts", v: muts, set: setMuts, lo: 1, hi: 4096 },
            { label: "L", v: l, set: setL, lo: 0, hi: n - 1 },
            { label: "R", v: r, set: setR, lo: 0, hi: n - 1 },
          ].map((x) => (
            <label key={x.label} className="text-xs font-semibold text-slate-600">
              {x.label}
              <input
                type="number"
                value={x.v}
                min={x.lo}
                max={x.hi}
                onChange={(e) => x.set(clamp(Number(e.target.value) || 0, x.lo, x.hi))}
                className="mt-2 w-full px-3 py-2 rounded-xl border border-slate-200 bg-white text-slate-900 text-xs font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1B74E4]/30"
              />
            </label>
          ))}
        </div>

        <div className="mt-3 text-xs text-slate-600">
          ops_total (turns × muts): <span className="font-extrabold text-slate-900">{opsTotal}</span> · range:{" "}
          <span className="font-extrabold text-slate-900">
            [{l}..{r}]
          </span>{" "}
          · len: <span className="font-extrabold text-slate-900">{rangeLen}</span>
        </div>
      </Card>

      {err ? <div className="text-xs font-semibold text-red-700">{err}</div> : null}

      {/* Seller container (pitch) */}
      <Card title="🎯 v41 — The “trust unlock”" subtitle="queries only execute when receipts verify">
        <div className="text-xs text-slate-700 leading-relaxed">
          <span className="font-semibold">The claim:</span> You can’t get a query answer unless you present a valid receipt chain.
          <br />
          <br />
          <span className="font-semibold">What’s enforced:</span>
          <ul className="mt-1 ml-4 list-disc text-slate-700">
            <li>
              <span className="font-semibold">Determinism</span>: the receipt serializes stably and hashes to <code className="text-slate-900">drift_sha256</code>.
            </li>
            <li>
              <span className="font-semibold">Ancestry</span>: each receipt points to <code className="text-slate-900">prev_drift_sha256</code> (no forked story).
            </li>
            <li>
              <span className="font-semibold">Gating</span>: server stays <span className="font-extrabold">LOCKED</span> until chain verifies; only then it runs the query invariants.
            </li>
          </ul>
          <div className="mt-3">
            <span className="font-semibold">Translation:</span> this kills “demo theater.” You can ship stream + receipts, and anyone can verify that the query answer was permitted and correct.
          </div>
        </div>
      </Card>

      {/* Charts + stats */}
      <div className="grid gap-3 lg:grid-cols-[1.2fr_0.8fr] items-start">
        <div className="flex flex-col gap-3">
          <GateTimelineChart steps={pipelineSteps} />
          <WorkVsLogChart fwStepsSum={fwStepsSumN} logN={logNN} />
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <StatTile
            label="Gate"
            value={
              <span
                className="px-3 py-1 rounded-full border text-xs font-extrabold"
                style={{ borderColor: gateBadge.bd, background: gateBadge.bg, color: gateBadge.fg }}
              >
                {gateUnlocked ? "UNLOCKED" : queryOut ? "LOCKED" : "—"}
              </span>
            }
            sub={queryOut?.reason ? <span className="text-red-700">{String(queryOut.reason)}</span> : "server state"}
          />
          <StatTile
            label="Local drift check"
            value={
              <span
                className="px-3 py-1 rounded-full border text-xs font-extrabold"
                style={{ borderColor: receiptBadge.bd, background: receiptBadge.bg, color: receiptBadge.fg }}
              >
                {receiptBadge.label}
              </span>
            }
            sub="browser recompute"
          />
          <StatTile label="Mint LEAN_OK" value={mintOut ? (leafLeanOk ? "1 ✅" : "0 ❌") : "—"} sub="backend check" />
          <StatTile
            label="Query invariants"
            value={
              <span
                className="px-3 py-1 rounded-full border text-xs font-extrabold"
                style={{
                  ...(() => {
                    const bb = boolBadge(queryOut ? queryOk : null);
                    return { borderColor: bb.bd, background: bb.bg, color: bb.fg };
                  })(),
                }}
              >
                {queryOut ? (queryOk ? "✅ OK" : "❌ FAIL") : "—"}
              </span>
            }
            sub="range_ok + work_logN"
          />
          <StatTile label="sum_baseline" value={sumBaseline ?? "—"} sub="reference" />
          <StatTile label="sum_stream" value={sumStream ?? "—"} sub="gated result" />
          <StatTile
            label="wire_total_bytes"
            value={wireTotalBytes ? bytes(wireTotalBytes) : "—"}
            sub={wireTotalBytes ? `${wireTotalBytes} B` : "optional"}
          />
          <StatTile label="range_len" value={(qBytes as any)?.range_len ?? rangeLen} sub="query span" />
        </div>
      </div>

      {/* Receipt verifier (input-driven like v44) */}
      <Card title="Receipt verifier" right={<span className="px-3 py-1 rounded-full border text-xs font-extrabold" style={{ borderColor: inputBadge.bd, background: inputBadge.bg, color: inputBadge.fg }}>{inputBadge.label}</span>}>
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={receiptInput}
            onChange={(e) => setReceiptInput(e.target.value)}
            placeholder="Paste drift_sha256 here to compare against current leaf…"
            className="flex-1 min-w-[320px] px-3 py-2 rounded-xl border border-slate-200 bg-white text-slate-900 text-xs font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1B74E4]/30"
            style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" }}
          />
          <PillButton onClick={() => setReceiptInput(drift || "")}>Use current drift</PillButton>
        </div>

        <div className="mt-3 text-xs text-slate-500 leading-relaxed">
          <div>
            current drift_sha256: <code className="text-slate-900">{drift || "—"}</code>
          </div>
          <div className="mt-1">
            Note: this input compare is a UX helper; the real proof is the browser-side recompute (Local drift check) + backend LEAN_OK.
          </div>
        </div>
      </Card>

      {/* Chain + Receipt + Query details */}
      <div className="grid gap-3 lg:grid-cols-2 items-start">
        <ChainList chain={chainViz} />

        <div className="flex flex-col gap-3">
          <Card title="Current leaf receipt">
            <div className="text-xs text-slate-700 leading-relaxed">
              <div>
                drift_sha256: <code className="text-slate-900">{drift || "—"}</code>
              </div>
              <div>
                final_state_sha256: <code className="text-slate-900">{String(receipt?.final_state_sha256 || "—")}</code>
              </div>
              <div>
                prev_drift_sha256: <code className="text-slate-900">{String(receipt?.prev_drift_sha256 || "—")}</code>
              </div>
              <div>
                LEAN_OK: <code className="text-slate-900">{mintOut ? (leafLeanOk ? "1" : "0") : "—"}</code>
              </div>
            </div>
          </Card>

          <Card title="Query invariants">
            <div className="text-xs text-slate-700 leading-relaxed">
              <div>
                range_ok: <code className="text-slate-900">{rangeOk === null ? "—" : String(rangeOk)}</code>
              </div>
              <div>
                work_scales_with_logN: <code className="text-slate-900">{workLogOk === null ? "—" : String(workLogOk)}</code>
              </div>
              <div>
                sum_baseline: <code className="text-slate-900">{String(sumBaseline ?? "—")}</code>
              </div>
              <div>
                sum_stream: <code className="text-slate-900">{String(sumStream ?? "—")}</code>
              </div>
              <div className="mt-2 pt-2 border-t border-slate-200">
                ops_total: <code className="text-slate-900">{(qBytes as any)?.ops_total ?? opsTotal ?? "—"}</code>
              </div>
              <div>
                range_len: <code className="text-slate-900">{(qBytes as any)?.range_len ?? rangeLen}</code>
              </div>
              <div>
                fw_steps_sum: <code className="text-slate-900">{(qBytes as any)?.fw_steps_sum ?? "—"}</code> / logN{" "}
                <code className="text-slate-900">{(qBytes as any)?.logN ?? "—"}</code>
              </div>
            </div>
          </Card>
        </div>

        {/* Raw */}
        <div className="lg:col-span-2">
          <Card title="Raw responses">
            <div className="mt-2 grid gap-3 lg:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-extrabold text-slate-900">mint</div>
                <pre className="mt-2 text-xs text-slate-900 whitespace-pre-wrap">{mintOut ? JSON.stringify(mintOut, null, 2) : "—"}</pre>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs font-extrabold text-slate-900">query</div>
                <pre className="mt-2 text-xs text-slate-900 whitespace-pre-wrap">{queryOut ? JSON.stringify(queryOut, null, 2) : "—"}</pre>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Endpoint footer */}
      <div className="mt-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600">
        Endpoints: <code className="text-slate-900">POST /api/wirepack/v41/mint</code> ·{" "}
        <code className="text-slate-900">POST /api/wirepack/v41/query</code>
      </div>
    </div>
  );
};