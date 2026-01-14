import React, { useMemo, useState } from "react";
import { useVisitHistory, type VisitItem } from "../hooks/useVisitHistory";

type Props = {
  kg: "personal" | "work";
  topicWa?: string;
  threadId?: string;
  pageSize?: number;
};

function fmtTs(ts: number) {
  try { return new Date(ts).toLocaleString(); } catch { return String(ts); }
}
function seconds(n?: number | null) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${Math.round(n)}s`;
}

export default function VisitHistoryPanel({
  kg, topicWa, threadId, pageSize = 50,
}: Props) {
  const { items, loadMore, hasMore, loading, error, refresh } = useVisitHistory({
    kg, topicWa, threadId, pageSize,
  });

  const grouped = useMemo(() => {
    const byHost = new Map<string, { host: string; totalDwell: number; count: number; rows: VisitItem[] }>();
    for (const v of items) {
      const host = (v.host || "(unknown)").toString();
      const g = byHost.get(host) || { host, totalDwell: 0, count: 0, rows: [] };
      g.count += 1;
      g.totalDwell += Number(v.duration_s || 0);
      g.rows.push(v);
      byHost.set(host, g);
    }
    return Array.from(byHost.values()).sort((a, b) => b.totalDwell - a.totalDwell);
  }, [items]);

  const [clearing, setClearing] = useState<string | null>(null);
  const [clearingAll, setClearingAll] = useState(false);

  async function clearByHost(host: string) {
    setClearing(host);
    try {
      await fetch("/api/kg/forget", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kg, scope: "visits", host })
      });
      await refresh();
    } finally { setClearing(null); }
  }

  async function clearAllForTopic() {
    if (!topicWa && !threadId) return;
    setClearingAll(true);
    try {
      const body: any = { kg, scope: "visits" };
      if (topicWa) body.topic_wa = topicWa;
      await fetch("/api/kg/forget", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      await refresh();
    } finally { setClearingAll(false); }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <h3 style={{ margin: 0 }}>Visit History</h3>
        {topicWa ? <code style={{ opacity: 0.7 }}>{topicWa}</code> : null}
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <button onClick={refresh} disabled={loading}>Refresh</button>
          <button onClick={clearAllForTopic} disabled={clearingAll || loading || (!topicWa && !threadId)}>
            {clearingAll ? "Clearing…" : "Clear All (this topic)"}
          </button>
        </div>
      </div>

      {error ? <div style={{ color: "crimson" }}>Error: {(error as any)?.message || "failed to load"}</div> : null}

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {grouped.map((g) => (
          <div key={g.host} style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 12, background: "#fff" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <strong>{g.host}</strong>
              <span style={{ opacity: 0.7 }}>• {g.count} events • {Math.round(g.totalDwell)}s total</span>
              <button
                style={{ marginLeft: "auto" }}
                onClick={() => clearByHost(g.host)}
                disabled={clearing === g.host || loading}
                title="Delete all visit rows for this host"
              >
                {clearing === g.host ? "Clearing…" : "Clear host"}
              </button>
            </div>

            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ textAlign: "left" }}>
                  <th style={{ padding: "6px 8px" }}>When</th>
                  <th style={{ padding: "6px 8px" }}>Kind</th>
                  <th style={{ padding: "6px 8px" }}>Title</th>
                  <th style={{ padding: "6px 8px" }}>URI</th>
                  <th style={{ padding: "6px 8px" }}>Dwell</th>
                </tr>
              </thead>
              <tbody>
                {g.rows.slice(0, 10).map((v) => (
                  <tr key={v.id} style={{ borderTop: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "6px 8px", whiteSpace: "nowrap" }}>{fmtTs(v.ts)}</td>
                    <td style={{ padding: "6px 8px" }}>{v.kind || "page"}</td>
                    <td style={{ padding: "6px 8px" }}>{v.title || "—"}</td>
                    <td style={{ padding: "6px 8px" }}>
                      <code style={{ opacity: 0.8 }}>{v.uri || v.href || "—"}</code>
                    </td>
                    <td style={{ padding: "6px 8px" }}>{seconds(v.duration_s)}</td>
                  </tr>
                ))}
                {g.rows.length > 10 ? (
                  <tr>
                    <td colSpan={5} style={{ padding: "6px 8px", opacity: 0.7 }}>
                      + {g.rows.length - 10} more…
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={loadMore} disabled={!hasMore || loading}>
          {loading ? "Loading…" : hasMore ? "Load more" : "No more"}
        </button>
        <span style={{ opacity: 0.6 }}>
          Loaded {items.length} item{items.length === 1 ? "" : "s"}
        </span>
      </div>
    </div>
  );
}