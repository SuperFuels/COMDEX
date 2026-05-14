// Glyph_Net_Browser/src/components/LedgerInspector.tsx
// Simple KG ledger inspector for Dev Tools dashboard.

import { useEffect, useState } from "react";

type LedgerEntry = {
  id?: string | number;
  kg?: string;
  uri?: string;
  op?: string;
  ts?: string;
  created_at?: string;
  [key: string]: any;
};

type ApiResponse =
  | LedgerEntry[]
  | {
      entries?: LedgerEntry[];
      results?: LedgerEntry[];
      data?: LedgerEntry[];
    };

function extractEntries(json: ApiResponse): LedgerEntry[] {
  if (Array.isArray(json)) return json;

  if (Array.isArray(json.entries)) return json.entries;
  if (Array.isArray(json.results)) return json.results;
  if (Array.isArray(json.data)) return json.data;

  return [];
}

export default function LedgerInspector() {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(
        "/api/kg/ledger/entries?kg=personal&limit=100",
        {
          headers: { Accept: "application/json" },
        }
      );

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const json = (await res.json()) as ApiResponse;
      const list = extractEntries(json);
      setEntries(list);
    } catch (e: any) {
      console.error("LedgerInspector error:", e);
      setError(e?.message || "Failed to load ledger entries");
      setEntries([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const selected = selectedIndex != null ? entries[selectedIndex] : null;

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 12,
        color: "#e5e7eb",
      }}
    >
      {/* Toolbar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            type="button"
            onClick={load}
            disabled={loading}
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #0ea5e9",
              background: loading ? "#0369a1" : "#0ea5e9",
              color: "#f9fafb",
              fontSize: 12,
              cursor: loading ? "default" : "pointer",
            }}
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
          <span style={{ fontSize: 12, opacity: 0.75 }}>
            {entries.length} entr{entries.length === 1 ? "y" : "ies"} (personal)
          </span>
        </div>

        {error && (
          <span style={{ fontSize: 12, color: "#fca5a5" }}>
            ⚠ {error}
          </span>
        )}
      </div>

      {/* Table + details */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1.4fr",
          gap: 12,
          height: "100%",
          minHeight: 0,
        }}
      >
        {/* Table */}
        <div
          style={{
            borderRadius: 8,
            border: "1px solid #1f2937",
            background: "#020617",
            overflow: "auto",
          }}
        >
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: 12,
            }}
          >
            <thead>
              <tr
                style={{
                  background: "#020617",
                  position: "sticky",
                  top: 0,
                  zIndex: 1,
                }}
              >
                <th style={thStyle}>#</th>
                <th style={thStyle}>Op</th>
                <th style={thStyle}>URI</th>
                <th style={thStyle}>KG</th>
                <th style={thStyle}>Time</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, idx) => {
                const isActive = idx === selectedIndex;
                const time =
                  (e.ts as string) ||
                  (e.created_at as string) ||
                  "";

                return (
                  <tr
                    key={e.id ?? idx}
                    onClick={() =>
                      setSelectedIndex(isActive ? null : idx)
                    }
                    style={{
                      cursor: "pointer",
                      background: isActive ? "#0f172a" : "transparent",
                    }}
                  >
                    <td style={tdStyle}>{idx + 1}</td>
                    <td style={tdStyle}>{e.op ?? ""}</td>
                    <td style={{ ...tdStyle, maxWidth: 260 }}>
                      <span
                        style={{
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          display: "inline-block",
                          maxWidth: "100%",
                        }}
                        title={String(e.uri ?? "")}
                      >
                        {e.uri ?? ""}
                      </span>
                    </td>
                    <td style={tdStyle}>{e.kg ?? ""}</td>
                    <td style={tdStyle}>{time}</td>
                  </tr>
                );
              })}

              {!loading && entries.length === 0 && !error && (
                <tr>
                  <td
                    colSpan={5}
                    style={{
                      ...tdStyle,
                      textAlign: "center",
                      opacity: 0.7,
                    }}
                  >
                    No ledger entries returned.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* JSON detail panel */}
        <div
          style={{
            borderRadius: 8,
            border: "1px solid #1f2937",
            background: "#020617",
            padding: 8,
            overflow: "auto",
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas",
            fontSize: 11,
          }}
        >
          {selected ? (
            <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>
              {JSON.stringify(selected, null, 2)}
            </pre>
          ) : (
            <span style={{ opacity: 0.7 }}>
              Select a row to inspect full JSON for that ledger entry.
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "6px 8px",
  borderBottom: "1px solid #1f2937",
  fontWeight: 600,
  color: "#9ca3af",
};

const tdStyle: React.CSSProperties = {
  padding: "4px 8px",
  borderBottom: "1px solid #111827",
  color: "#e5e7eb",
};