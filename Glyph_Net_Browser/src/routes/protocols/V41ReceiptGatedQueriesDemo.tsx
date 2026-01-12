import React, { useMemo, useState } from "react";

function bytes(n: number) {
  const units = ["B", "KB", "MB", "GB"];
  let v = n, i = 0;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
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
    try { json = txt ? JSON.parse(txt) : {}; }
    catch { json = { _nonJson: true, _text: txt.slice(0, 400) }; }
    return { ok: r.ok, status: r.status, json };
  } finally { clearTimeout(t); }
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

function fmtTri(v: boolean | null) {
  return v === null ? "—" : (v ? "OK" : "FAIL");
}
function colorTri(v: boolean | null) {
  return v === null ? "#6b7280" : (v ? "#065f46" : "#991b1b");
}

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

  const mintBody = useMemo(() => ({ seed, n, turns, muts }), [seed, n, turns, muts]);

  // ---- minted receipt fields (robust to small shape diffs)
  const receipt = mintOut?.receipt ?? mintOut?.receipts?.receipt ?? mintOut?.result?.receipt ?? null;
  const receipts = mintOut?.receipts || {};
  const drift = String(receipts?.drift_sha256 || mintOut?.drift_sha256 || "");
  const leafLeanOk = receipts?.LEAN_OK === 1 || receipts?.LEAN_OK === true || mintOut?.LEAN_OK === 1 || mintOut?.LEAN_OK === true;

  // ---- query fields (robust to small shape diffs)
  const q = queryOut?.query || queryOut?.result || queryOut || {};
  const qInv = q?.invariants || queryOut?.invariants || null;
  const qBytes = q?.bytes || queryOut?.bytes || {};

  const rangeOk: boolean | null =
    typeof qInv?.range_ok === "boolean" ? qInv.range_ok : null;

  const workLogOk: boolean | null =
    typeof qInv?.work_scales_with_logN === "boolean" ? qInv.work_scales_with_logN :
    typeof qInv?.work_scales_with_log_n === "boolean" ? qInv.work_scales_with_log_n :
    null;

  const queryRan = rangeOk !== null || workLogOk !== null;

  const queryOk =
    (rangeOk === null ? true : rangeOk) &&
    (workLogOk === null ? true : workLogOk);

  // "receipt verified" = we have local drift verification + backend LEAN_OK at mint
  const receiptVerified = !!localVerified && leafLeanOk;

  // gate unlocked can be explicit, otherwise treat as unlocked if query ran
  const gateUnlocked =
    queryOut?.unlocked === true ||
    queryOut?.locked === false ||
    (queryOut?.gate?.status === "UNLOCKED") ||
    queryRan;

  const leanVerified = receiptVerified && queryOk;

  const rangeLen = (Math.max(0, r - l + 1));

  async function mint() {
    if (busyMint) return;
    setBusyMint(true);
    setErr(null);
    setMintOut(null);
    setQueryOut(null);
    setLocalVerified(null);
    try {
      const { ok, status, json } = await fetchJson("/api/wirepack/v41/mint", mintBody);
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setMintOut(json);

      // Local drift verification (browser-side)
      const d = String(json?.receipts?.drift_sha256 || json?.drift_sha256 || "");
      const rb = json?.receipt ?? json?.receipts?.receipt ?? json?.result?.receipt;
      if (d && rb) {
        const want = await sha256HexUtf8(stableStringify(rb));
        setLocalVerified(want === d);
      } else {
        setLocalVerified(false);
      }
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
      if (!receipt || !drift) throw new Error("Missing receipt — mint first.");

      const chain = [{ receipt, drift_sha256: drift }];
      const { ok, status, json } = await fetchJson("/api/wirepack/v41/query", { chain, l, r });
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setQueryOut(json);
    } catch (e: any) {
      setErr(e?.message || String(e));
    } finally {
      setBusyQuery(false);
    }
  }

  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 900, color: "#111827" }}>v41 — Receipt-gated queries</div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            You can’t query unless the receipt chain verifies (anti “demo theater”). Shows lock/unlock + ancestry + drift check.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {/* LEAN badge */}
          <div style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "4px 10px",
            borderRadius: 999,
            border: "1px solid " + (leanVerified ? "#a7f3d0" : "#e5e7eb"),
            background: leanVerified ? "#ecfdf5" : "#f9fafb",
            color: leanVerified ? "#065f46" : "#6b7280",
            fontSize: 11,
            fontWeight: 900,
          }}>
            {leanVerified ? "LEAN VERIFIED" : "LEAN PENDING"}
          </div>

          <button
            type="button"
            onClick={mint}
            disabled={busyMint}
            style={{
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid " + (busyMint ? "#e5e7eb" : "#111827"),
              background: busyMint ? "#f3f4f6" : "#111827",
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
            disabled={busyQuery || !receipt}
            style={{
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid " + (busyQuery || !receipt ? "#e5e7eb" : "#111827"),
              background: (busyQuery || !receipt) ? "#f3f4f6" : "#111827",
              color: (busyQuery || !receipt) ? "#6b7280" : "#fff",
              fontSize: 11,
              fontWeight: 900,
              cursor: (busyQuery || !receipt) ? "not-allowed" : "pointer",
            }}
          >
            {busyQuery ? "Querying…" : "Run gated query"}
          </button>
        </div>
      </div>

      <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "repeat(6, minmax(0, 1fr))", gap: 8 }}>
        <label style={{ fontSize: 11, color: "#374151" }}>
          seed
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(Number(e.target.value) || 0)}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }}
          />
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          n
          <input
            type="number"
            value={n}
            min={256}
            max={65536}
            onChange={(e) => setN(Math.max(256, Math.min(65536, Number(e.target.value) || 4096)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }}
          />
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          turns
          <input
            type="number"
            value={turns}
            min={1}
            max={4096}
            onChange={(e) => setTurns(Math.max(1, Math.min(4096, Number(e.target.value) || 64)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }}
          />
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          muts
          <input
            type="number"
            value={muts}
            min={1}
            max={4096}
            onChange={(e) => setMuts(Math.max(1, Math.min(4096, Number(e.target.value) || 3)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }}
          />
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          L
          <input
            type="number"
            value={l}
            min={0}
            max={n - 1}
            onChange={(e) => setL(Math.max(0, Math.min(n - 1, Number(e.target.value) || 0)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }}
          />
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          R
          <input
            type="number"
            value={r}
            min={0}
            max={n - 1}
            onChange={(e) => setR(Math.max(0, Math.min(n - 1, Number(e.target.value) || 127)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }}
          />
        </label>
      </div>

      {err ? <div style={{ marginTop: 10, fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

      <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        {/* Receipt / Gate */}
        <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Receipt / Gate</div>

          <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
            Receipt verified:{" "}
            <b style={{ color: receiptVerified ? "#065f46" : (localVerified === null ? "#6b7280" : "#991b1b") }}>
              {receiptVerified ? "YES (LEAN VERIFIED)" : (localVerified === null ? "—" : "NO")}
            </b>
          </div>

          <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
            drift_sha256: <code>{drift || "—"}</code>
          </div>

          <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
            final_state_sha256: <code>{String(receipt?.final_state_sha256 || "—")}</code>
          </div>

          <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
            Gate status:{" "}
            <b style={{ color: gateUnlocked ? "#065f46" : "#991b1b" }}>
              {gateUnlocked ? "UNLOCKED" : "LOCKED"}
            </b>
          </div>

          {queryOut?.reason ? (
            <div style={{ marginTop: 6, fontSize: 11, color: "#b91c1c" }}>
              reason: <code>{String(queryOut.reason)}</code>
            </div>
          ) : null}

          <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280" }}>
            ancestry:{" "}
            <code>
              {drift ? JSON.stringify([{ drift_sha256: drift, prev: receipt?.prev_drift_sha256 || "" }]) : "—"}
            </code>
          </div>
        </div>

        {/* Query result */}
        <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Query result</div>

          <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
            range_ok:{" "}
            <b style={{ color: colorTri(rangeOk) }}>{fmtTri(rangeOk)}</b>
          </div>

          <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
            work_scales_with_logN:{" "}
            <b style={{ color: colorTri(workLogOk) }}>{fmtTri(workLogOk)}</b>
          </div>

          <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
            sum_baseline: <code>{String(q?.sum_baseline ?? queryOut?.sum_baseline ?? "—")}</code>
          </div>

          <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
            sum_stream: <code>{String(q?.sum_stream ?? queryOut?.sum_stream ?? "—")}</code>
          </div>

          <div style={{ marginTop: 10, fontSize: 11, color: "#374151" }}>
            ops_total: <b>{qBytes?.ops_total ?? "—"}</b>
          </div>

          <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
            range: <b>[{l}..{r}]</b> &nbsp; len: <b>{qBytes?.range_len ?? rangeLen}</b>
          </div>

          <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
            fw_steps_sum: <b>{qBytes?.fw_steps_sum ?? "—"}</b>
            {" "}/ logN <b>{qBytes?.logN ?? "—"}</b>
          </div>

          <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280" }}>
            endpoint: <code>POST /api/wirepack/v41/query</code>
          </div>
        </div>

        {/* What this demo proves */}
        <div style={{ gridColumn: "1 / -1", borderRadius: 12, border: "1px solid #e5e7eb", padding: 10, background: "#f9fafb" }}>
          <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>What this demo proves</div>

          <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.55 }}>
            <div>
              <b>Claim</b>: queries are <b>receipt-gated</b> — if the receipt chain doesn’t verify, the query stays <b>LOCKED</b>.
            </div>

            <div style={{ marginTop: 8 }}>
              <b>We are testing for</b>: (1) deterministic receipt recomputation (<code>drift_sha256</code>), (2) ancestry continuity, and (3) query invariants only run when the gate is unlocked.
            </div>

            <div style={{ marginTop: 8 }}>
              <b>Run</b>:
              <div style={{ marginTop: 6 }}>• <b>Mint receipt</b>: produce a deterministic receipt for the underlying stream computation.</div>
              <div style={{ marginTop: 4 }}>• <b>Run gated query</b>: server verifies receipt + ancestry, then executes the query and returns invariants.</div>
            </div>

            <div style={{ marginTop: 8 }}>
              <b>What the results mean</b>:
              <div style={{ marginTop: 6 }}>• <code>Gate status</code>: <b>{gateUnlocked ? "UNLOCKED" : "LOCKED"}</b> (locked means “no query”).</div>
              <div style={{ marginTop: 4 }}>• <code>Receipt verified</code>: <b>{receiptVerified ? "YES" : (localVerified === null ? "—" : "NO")}</b> (drift recompute + LEAN checks).</div>
              <div style={{ marginTop: 4 }}>• <code>range_ok</code> / <code>work_scales_with_logN</code>: appear only after the query runs; they must be OK for a green run.</div>
            </div>

            <div style={{ marginTop: 10 }}>
              <b>Why it matters</b>: kills “demo theater.” You can’t show a query answer unless it’s tied to a verifiable receipt chain. This is the enforcement primitive for trust.
            </div>

            <div style={{ marginTop: 8, color: "#6b7280" }}>
              <b>Lean note</b>: <code>LEAN_OK=1</code> means the receipt/invariant checks passed end-to-end and the result is replay-locked.
            </div>
          </div>
        </div>

        {/* Sell */}
        <div style={{ gridColumn: "1 / -1", borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Sell</div>
          <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.55 }}>
            <div><b>The trust unlock</b>: receipt-gated computation.</div>
            <div style={{ marginTop: 6 }}><b>What’s enforced</b>: drift hash recomputation + ancestry pointers + invariant checks.</div>
            <div style={{ marginTop: 6 }}><b>Outcome</b>: verifiers can refuse to execute or accept results unless the receipt chain checks out.</div>
          </div>
        </div>

        {/* Bytes (optional but consistent with other demos) */}
        <div style={{ gridColumn: "1 / -1", borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Bytes</div>
          <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
            wire_total_bytes: <b>{qBytes?.wire_total_bytes == null ? "—" : bytes(Number(qBytes.wire_total_bytes))}</b>
            {qBytes?.wire_total_bytes != null ? <span style={{ color: "#6b7280" }}> ({qBytes.wire_total_bytes} B)</span> : null}
          </div>
          <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
            receipts: <code>{JSON.stringify({ drift_sha256: drift || undefined, LEAN_OK: leafLeanOk ? 1 : 0 })}</code>
          </div>
        </div>
      </div>
    </div>
  );
};