// src/components/MeshPolicyPanel.tsx

import { useEffect, useState } from "react";

type MeshPolicySnapshot = {
  default_limit_pho?: string | number;
  emergency_mode_enabled?: boolean;
  emergency_limit_pho?: string | number;
  limit_pct_of_balance_bps?: number;
  overrides?: Array<{
    account?: string;
    limit_pho?: string | number;
    reason?: string;
  }>;
  // allow any extra fields without breaking UI
  [key: string]: any;
};

export default function MeshPolicyPanel() {
  const [snapshot, setSnapshot] = useState<MeshPolicySnapshot | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchSnapshot() {
      setLoading(true);
      setError(null);

      try {
        const resp = await fetch("/api/mesh/policy/snapshot");
        if (!resp.ok) {
          const txt = await resp.text();
          throw new Error(
            txt || `HTTP ${resp.status} from /api/mesh/policy/snapshot`
          );
        }
        const data = (await resp.json()) as MeshPolicySnapshot;
        if (!cancelled) {
          setSnapshot(data);
        }
      } catch (e: any) {
        if (!cancelled) {
          console.error("[MeshPolicyPanel] fetch failed:", e);
          setError(e?.message || "Failed to load mesh policy snapshot.");
          setSnapshot(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void fetchSnapshot();
    return () => {
      cancelled = true;
    };
  }, []);

  const defaultLimit =
    snapshot?.default_limit_pho ??
    snapshot?.default_limit ??
    snapshot?.limit_pho;

  const overrides = snapshot?.overrides ?? [];

  return (
    <div
      style={{
        padding: 16,
        maxWidth: 960,
        margin: "0 auto",
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      {/* Header */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: "#0f172a",
            }}
          >
            Mesh Offline Credit Policy (dev)
          </div>
          <div
            style={{
              fontSize: 12,
              color: "#6b7280",
            }}
          >
            Live snapshot from <code>/api/mesh/policy/snapshot</code>. This will
            eventually be wired into the full GMA admin panel.
          </div>
        </div>
      </header>

      {/* Status strip */}
      <section
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 12,
          fontSize: 12,
          color: "#4b5563",
        }}
      >
        {loading && <div>Loading mesh policy snapshot…</div>}
        {!loading && error && (
          <div style={{ color: "#b91c1c" }}>{error}</div>
        )}
        {!loading && !error && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 12,
              alignItems: "center",
            }}
          >
            <div>
              <span style={{ color: "#6b7280" }}>Default offline limit: </span>
              <strong>{defaultLimit ?? "—"} PHO</strong>
            </div>

            <div>
              <span style={{ color: "#6b7280" }}>Emergency mode: </span>
              <strong>
                {snapshot?.emergency_mode_enabled ? "ENABLED" : "disabled"}
              </strong>
            </div>

            {snapshot?.emergency_limit_pho != null && (
              <div>
                <span style={{ color: "#6b7280" }}>Emergency limit: </span>
                <strong>{snapshot.emergency_limit_pho} PHO</strong>
              </div>
            )}

            {snapshot?.limit_pct_of_balance_bps != null && (
              <div>
                <span style={{ color: "#6b7280" }}>Balance fraction cap: </span>
                <strong>
                  {snapshot.limit_pct_of_balance_bps / 100.0}
                  %
                </strong>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Overrides table */}
      <section
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 12,
        }}
      >
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: "#0f172a",
            marginBottom: 4,
          }}
        >
          Per-account overrides
        </div>
        <div
          style={{
            fontSize: 11,
            color: "#9ca3af",
            marginBottom: 6,
          }}
        >
          Accounts with custom offline credit limits (e.g. merchants, infra,
          special cases).
        </div>

        {(!overrides || overrides.length === 0) && (
          <div
            style={{
              fontSize: 11,
              color: "#9ca3af",
            }}
          >
            No explicit overrides; all accounts use the default limit.
          </div>
        )}

        {overrides && overrides.length > 0 && (
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: 11,
            }}
          >
            <thead>
              <tr>
                <th
                  style={{
                    textAlign: "left",
                    padding: "4px 0",
                    borderBottom: "1px solid #e5e7eb",
                    fontWeight: 500,
                    color: "#6b7280",
                  }}
                >
                  Account
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: "4px 0",
                    borderBottom: "1px solid #e5e7eb",
                    fontWeight: 500,
                    color: "#6b7280",
                  }}
                >
                  Limit (PHO)
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: "4px 0",
                    borderBottom: "1px solid #e5e7eb",
                    fontWeight: 500,
                    color: "#6b7280",
                  }}
                >
                  Reason
                </th>
              </tr>
            </thead>
            <tbody>
              {overrides.map((ov, idx) => (
                <tr key={ov.account || idx}>
                  <td
                    style={{
                      padding: "3px 0",
                      color: "#111827",
                      fontFamily: "monospace",
                      fontSize: 11,
                    }}
                  >
                    {ov.account || "—"}
                  </td>
                  <td
                    style={{
                      padding: "3px 0",
                      color: "#111827",
                    }}
                  >
                    {ov.limit_pho ?? "—"}
                  </td>
                  <td
                    style={{
                      padding: "3px 0",
                      color: "#4b5563",
                    }}
                  >
                    {ov.reason || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Raw JSON view */}
      <section
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#f9fafb",
          padding: 12,
        }}
      >
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: "#0f172a",
            marginBottom: 4,
          }}
        >
          Raw snapshot (debug)
        </div>
        <pre
          style={{
            margin: 0,
            fontSize: 11,
            lineHeight: 1.4,
            color: "#374151",
            overflowX: "auto",
          }}
        >
{JSON.stringify(snapshot, null, 2)}
        </pre>
      </section>
    </div>
  );
}