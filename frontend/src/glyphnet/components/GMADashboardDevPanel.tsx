import { useEffect, useState } from "react";

type GMASnapshot = {
  photon_supply_pho?: string;
  tesseract_supply_tess?: string;
  reserves_pho_equiv?: string;
  equity_pho?: string;
  invariants?: {
    assets_pho?: string;
    liabilities_pho?: string;
    equity_pho?: string;
    check_ok?: boolean;
    notes?: string[];
  };
  mint_burn_log?: any[];
  reserve_log?: any[];
  // fallthrough for whatever else you return from the backend
  [key: string]: any;
};

export default function GMADashboardDevPanel() {
  const [snap, setSnap] = useState<GMASnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function fetchSnapshot() {
    setLoading(true);
    setErr(null);
    try {
      const res = await fetch("/api/gma/state/dev_snapshot");
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || `HTTP ${res.status}`);
      }
      const json = await res.json();
      // backend can return either { snapshot: {...} } or the snapshot itself
      const s: GMASnapshot = (json.snapshot || json) as GMASnapshot;
      setSnap(s);
    } catch (e: any) {
      console.error("[GMA] dev_snapshot failed:", e);
      setErr(e?.message || "Failed to load GMA snapshot");
      setSnap(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchSnapshot();
  }, []);

  const phoSupply = snap?.photon_supply_pho ?? "—";
  const tessSupply = snap?.tesseract_supply_tess ?? "—";
  const reservesPho = snap?.reserves_pho_equiv ?? "—";
  const equityPho = snap?.equity_pho ?? snap?.invariants?.equity_pho ?? "—";

  const mintBurnLog = (snap?.mint_burn_log || []) as any[];
  const reserveLog = (snap?.reserve_log || []) as any[];

  return (
    <section
      style={{
        borderRadius: 16,
        border: "1px solid #e5e7eb",
        background: "#ffffff",
        padding: 12,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      {/* Header */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 8,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "#0f172a",
            }}
          >
            GMA state (dev)
          </div>
          <div
            style={{
              fontSize: 11,
              color: "#6b7280",
            }}
          >
            Snapshot + invariants from <code>/api/gma/state/dev_snapshot</code>.
          </div>
        </div>
        <button
          type="button"
          onClick={fetchSnapshot}
          disabled={loading}
          style={{
            padding: "4px 10px",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            background: loading ? "#e5e7eb" : "#f9fafb",
            fontSize: 11,
            cursor: loading ? "default" : "pointer",
          }}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      {err && (
        <div style={{ fontSize: 11, color: "#b91c1c" }}>
          {err}
        </div>
      )}

      {/* Big numbers row */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          fontSize: 11,
          color: "#111827",
        }}
      >
        <MetricPill label="PHO supply" value={`${phoSupply} PHO`} />
        <MetricPill label="TESS supply" value={`${tessSupply} TESS`} />
        <MetricPill label="Reserves (PHO eq.)" value={`${reservesPho} PHO`} />
        <MetricPill
          label="Equity"
          value={`${equityPho} PHO`}
          tone={
            snap?.invariants?.check_ok === false
              ? "bad"
              : snap?.invariants?.check_ok === true
              ? "good"
              : "neutral"
          }
        />
      </div>

      {/* Invariants summary */}
      {snap?.invariants && (
        <div
          style={{
            marginTop: 4,
            padding: 8,
            borderRadius: 12,
            border: "1px dashed #e5e7eb",
            background: "#f9fafb",
            fontSize: 11,
            color: "#4b5563",
          }}
        >
          <div style={{ marginBottom: 2, fontWeight: 500 }}>
            Invariants (assets – liabilities = equity)
          </div>
          <div>
            Assets:{" "}
            <code>{snap.invariants.assets_pho ?? "?"} PHO</code> · Liabilities:{" "}
            <code>{snap.invariants.liabilities_pho ?? "?"} PHO</code> · Equity:{" "}
            <code>{snap.invariants.equity_pho ?? "?"} PHO</code>{" "}
            {snap.invariants.check_ok === true && (
              <span style={{ color: "#16a34a", marginLeft: 4 }}>✓ OK</span>
            )}
            {snap.invariants.check_ok === false && (
              <span style={{ color: "#b91c1c", marginLeft: 4 }}>⚠︎ breach</span>
            )}
          </div>
          {Array.isArray(snap.invariants.notes) &&
            snap.invariants.notes.length > 0 && (
              <ul
                style={{
                  margin: "4px 0 0",
                  paddingLeft: 18,
                }}
              >
                {snap.invariants.notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            )}
        </div>
      )}

      {/* Logs */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          marginTop: 6,
        }}
      >
        {/* Mint / burn log */}
        <div
          style={{
            flex: 1,
            minWidth: 220,
            fontSize: 11,
            color: "#4b5563",
          }}
        >
          <div
            style={{
              marginBottom: 4,
              fontWeight: 500,
              color: "#111827",
            }}
          >
            Mint / burn log (latest)
          </div>
          {mintBurnLog.length === 0 ? (
            <div style={{ fontSize: 11, color: "#9ca3af" }}>No entries.</div>
          ) : (
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 11,
              }}
            >
              <thead>
                <tr style={{ textAlign: "left", color: "#6b7280" }}>
                  <th style={{ padding: "2px 4px" }}>Time</th>
                  <th style={{ padding: "2px 4px" }}>Kind</th>
                  <th style={{ padding: "2px 4px" }}>Amount</th>
                  <th style={{ padding: "2px 4px" }}>Reason</th>
                </tr>
              </thead>
              <tbody>
                {mintBurnLog.slice(-5).reverse().map((row: any) => {
                  const ts = row.created_at_ms
                    ? new Date(row.created_at_ms).toLocaleString()
                    : "—";
                  const kind = row.kind || row.op || "MINT/BURN";
                  return (
                    <tr key={row.id || row.created_at_ms || Math.random()}>
                      <td style={{ padding: "2px 4px" }}>{ts}</td>
                      <td style={{ padding: "2px 4px" }}>{kind}</td>
                      <td style={{ padding: "2px 4px" }}>
                        {row.amount_pho ?? "?"} PHO
                      </td>
                      <td style={{ padding: "2px 4px" }}>
                        {row.reason || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Reserve log */}
        <div
          style={{
            flex: 1,
            minWidth: 220,
            fontSize: 11,
            color: "#4b5563",
          }}
        >
          <div
            style={{
              marginBottom: 4,
              fontWeight: 500,
              color: "#111827",
            }}
          >
            Reserve log (latest)
          </div>
          {reserveLog.length === 0 ? (
            <div style={{ fontSize: 11, color: "#9ca3af" }}>No entries.</div>
          ) : (
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 11,
              }}
            >
              <thead>
                <tr style={{ textAlign: "left", color: "#6b7280" }}>
                  <th style={{ padding: "2px 4px" }}>Time</th>
                  <th style={{ padding: "2px 4px" }}>Kind</th>
                  <th style={{ padding: "2px 4px" }}>Asset</th>
                  <th style={{ padding: "2px 4px" }}>Δ PHO</th>
                </tr>
              </thead>
              <tbody>
                {reserveLog.slice(-5).reverse().map((row: any) => {
                  const ts = row.created_at_ms
                    ? new Date(row.created_at_ms).toLocaleString()
                    : "—";
                  const kind = row.kind || row.op || "DEPOSIT/REDEMP";
                  return (
                    <tr key={row.id || row.created_at_ms || Math.random()}>
                      <td style={{ padding: "2px 4px" }}>{ts}</td>
                      <td style={{ padding: "2px 4px" }}>{kind}</td>
                      <td style={{ padding: "2px 4px" }}>
                        {row.asset_symbol || row.asset || "—"}
                      </td>
                      <td style={{ padding: "2px 4px" }}>
                        {row.pho_delta ?? row.delta_pho ?? "?"} PHO
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </section>
  );
}

type MetricPillProps = {
  label: string;
  value: string;
  tone?: "good" | "bad" | "neutral";
};

function MetricPill({ label, value, tone = "neutral" }: MetricPillProps) {
  const bg =
    tone === "good" ? "#ecfdf5" : tone === "bad" ? "#fef2f2" : "#f9fafb";
  const border =
    tone === "good" ? "#bbf7d0" : tone === "bad" ? "#fecaca" : "#e5e7eb";
  const color =
    tone === "good" ? "#166534" : tone === "bad" ? "#b91c1c" : "#111827";

  return (
    <div
      style={{
        borderRadius: 999,
        padding: "6px 10px",
        border: `1px solid ${border}`,
        background: bg,
        minWidth: 140,
      }}
    >
      <div
        style={{
          fontSize: 10,
          color: "#6b7280",
          marginBottom: 2,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          color,
        }}
      >
        {value}
      </div>
    </div>
  );
}