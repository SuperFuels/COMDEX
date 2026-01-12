import React, { useMemo, useState } from "react";

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

function Badge(props: { ok: boolean | null; label: string }) {
  const ok = props.ok === true;
  const unknown = props.ok == null;
  const bg = unknown ? "#f3f4f6" : ok ? "#ecfdf5" : "#fef2f2";
  const fg = unknown ? "#374151" : ok ? "#065f46" : "#991b1b";
  const border = unknown ? "#e5e7eb" : ok ? "#a7f3d0" : "#fecaca";
  return (
    <span
      style={{
        padding: "5px 10px",
        borderRadius: 999,
        border: `1px solid ${border}`,
        background: bg,
        color: fg,
        fontSize: 11,
        fontWeight: 900,
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        whiteSpace: "nowrap",
      }}
    >
      <span style={{ fontSize: 12 }}>{unknown ? "•" : ok ? "✅" : "⚠️"}</span>
      {props.label}
    </span>
  );
}

export const V30SumOverQDemo: React.FC = () => {
  const [seed, setSeed] = useState(1337);
  const [n, setN] = useState(4096);
  const [turns, setTurns] = useState(64);
  const [muts, setMuts] = useState(3);
  const [q, setQ] = useState(128);

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [out, setOut] = useState<any | null>(null);

  const body = useMemo(() => ({ seed, n, turns, muts, q }), [seed, n, turns, muts, q]);

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setOut(null);
    try {
      const { ok, status, json } = await fetchJson("/api/wirepack/v30/run", body);
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setOut(json);
    } catch (e: any) {
      setErr(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  const inv = out?.invariants;
  const b = out?.bytes;
  const receipts = out?.receipts || {};
  const leanOkVal = receipts?.LEAN_OK;
  const leanOk = leanOkVal == null ? null : Boolean(Number(leanOkVal));
  const drift = typeof receipts?.drift_sha256 === "string" ? receipts.drift_sha256 : null;

  const sumOk = inv?.sum_ok == null ? null : Boolean(inv.sum_ok);
  const scalesOk = inv?.work_scales_with_Q == null ? null : Boolean(inv.work_scales_with_Q);

  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <div style={{ fontSize: 13, fontWeight: 900, color: "#111827" }}>v30 — Sum over Q</div>
            <Badge ok={leanOk} label={`LEAN_OK: ${leanOk === true ? "OK" : leanOk === false ? "FAIL" : "—"}`} />
          </div>
          <div style={{ fontSize: 11, color: "#6b7280" }}>
            Tracks only indices in <b>Q</b> while maintaining an incremental sum; compares to full replay baseline.
          </div>
        </div>

        <button
          type="button"
          onClick={run}
          disabled={busy}
          style={{
            padding: "6px 12px",
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

      <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: 8 }}>
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
          |Q|
          <input
            type="number"
            value={q}
            min={1}
            max={4096}
            onChange={(e) => setQ(Math.max(1, Math.min(4096, Number(e.target.value) || 128)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }}
          />
        </label>
      </div>

      {err ? <div style={{ marginTop: 10, fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

      {out ? (
        <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827", display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              Invariant
              <Badge ok={sumOk} label={`sum_ok: ${sumOk === true ? "OK" : sumOk === false ? "FAIL" : "—"}`} />
              <Badge ok={scalesOk} label={`work_scales_with_Q: ${scalesOk === true ? "OK" : scalesOk === false ? "FAIL" : "—"}`} />
            </div>

            <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
              sum_baseline: <code>{String(out?.sum_baseline ?? "—")}</code>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              sum_stream: <code>{String(out?.sum_stream ?? "—")}</code>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              final_state_sha256: <code>{String(out?.final_state_sha256 || "—")}</code>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              drift_sha256: <code>{drift || "—"}</code>
            </div>
          </div>

          <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Bytes</div>
            <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
              ops_total: <b>{b?.ops_total ?? "—"}</b>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              q_size: <b>{b?.q_size ?? "—"}</b> &nbsp; hits_in_Q: <b>{b?.hits_in_Q ?? "—"}</b>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              delta_bytes_total: <b>{b?.delta_bytes_total == null ? "—" : bytes(Number(b.delta_bytes_total))}</b>
              {b?.delta_bytes_total != null ? <span style={{ color: "#6b7280" }}> ({b.delta_bytes_total} B)</span> : null}
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              wire_total_bytes: <b>{b?.wire_total_bytes == null ? "—" : bytes(Number(b.wire_total_bytes))}</b>
              {b?.wire_total_bytes != null ? <span style={{ color: "#6b7280" }}> ({b.wire_total_bytes} B)</span> : null}
            </div>

            <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280" }}>
              receipts: <code>{JSON.stringify(receipts)}</code>
            </div>
          </div>

          {/* Explanation + Sell */}
          <div style={{ gridColumn: "1 / -1", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10, background: "#fff" }}>
              <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Explanation</div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.45 }}>
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  <li>
                    Choose a query set <b>Q</b> (|Q| indices) you care about.
                  </li>
                  <li>
                    Baseline replays all mutations and computes <code>SUM(state[i] for i in Q)</code>.
                  </li>
                  <li>
                    Streaming keeps only tracked values for indices in Q and maintains the sum via{" "}
                    <code>sum += (new - old)</code> (exact <code>BigInt</code>, not modulo wrap).
                  </li>
                  <li>
                    Receipt lock: the run emits a drift hash so the “lean” computation is tied to the same replay.
                  </li>
                </ul>
              </div>
            </div>

            <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10, background: "#fff" }}>
              <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Why it matters</div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.45 }}>
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  <li>
                    Work scales with <b>|Q|</b> (not <b>n</b>): you’re maintaining only what the query touches.
                  </li>
                  <li>
                    You can keep <b>query aggregates</b> (like SUM) correct without storing full state.
                  </li>
                  <li>
                    <b>LEAN_OK</b> is the signal that the lean path matched the replay invariants for this run.
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <div style={{ gridColumn: "1 / -1", borderRadius: 12, border: "1px solid #e5e7eb", padding: 10, background: "#f9fafb" }}>
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Endpoint</div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              <code>POST /api/wirepack/v30/run</code>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              params: <code>{JSON.stringify(out?.params || {}, null, 0)}</code>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};