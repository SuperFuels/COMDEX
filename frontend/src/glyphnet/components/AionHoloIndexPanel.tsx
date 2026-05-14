// /workspaces/COMDEX/Glyph_Net_Browser/src/components/AionHoloIndexPanel.tsx

import React, { useEffect, useState } from "react";

type HoloIndexItem = {
  holo_id: string;
  container_id: string;
  created_at: string;
  path: string;
  memory_seed_count?: number;
  rulebook_seed_count?: number;
  tags?: string[];
};

type HoloIndexResponse = {
  items: HoloIndexItem[];
  total: number;
  container_id?: string | null;
  tag?: string | null;
  seed?: string | null;
  slug?: string | null;
};

export type AionHoloIndexPanelProps = {
  activeHoloId: string | null;
  onSelectSnapshot: (id: string | null) => void;
};

export function AionHoloIndexPanel({
  activeHoloId,
  onSelectSnapshot,
}: AionHoloIndexPanelProps) {
  const [items, setItems] = useState<HoloIndexItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        // convenience slug for aion_memory::core
        const res = await fetch("/api/holo/index/aion-memory");
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const json = (await res.json()) as HoloIndexResponse;
        if (!cancelled) {
          setItems(json.items || []);
        }
      } catch (err) {
        if (!cancelled) {
          setError(String(err));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = items.filter((item) => {
    if (!filter.trim()) return true;
    const f = filter.toLowerCase();
    const haystack = [
      item.holo_id,
      item.container_id,
      item.path,
      ...(item.tags || []),
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(f);
  });

  return (
    <div
      style={{
        borderRadius: 8,
        border: "1px solid #e5e7eb",
        padding: 8,
        fontSize: 11,
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 8,
          alignItems: "baseline",
        }}
      >
        <div>
          <div style={{ fontWeight: 600 }}>AION Holo Snapshots</div>
          <div style={{ fontSize: 10, color: "#6b7280" }}>
            {items.length} snapshot{items.length === 1 ? "" : "s"}
          </div>
        </div>

        <input
          type="text"
          placeholder="Filter by tag / id…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={{
            borderRadius: 6,
            border: "1px solid #d1d5db",
            padding: "3px 6px",
            fontSize: 10,
            minWidth: 120,
          }}
        />
      </div>

      {!loading && !error && items.length > 0 && (
        <div style={{ fontSize: 10, color: "#9ca3af" }}>
          Click a snapshot to load it into the hologram.
        </div>
      )}

      {loading && (
        <div style={{ fontSize: 11, color: "#6b7280" }}>Loading index…</div>
      )}

      {error && (
        <div style={{ fontSize: 11, color: "#f97316" }}>
          Failed to load holo index: {error}
        </div>
      )}

      {!loading && !error && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
            maxHeight: 180,
            overflow: "auto",
          }}
        >
          {filtered.length === 0 && (
            <div style={{ fontSize: 11, color: "#9ca3af" }}>
              No snapshots match this filter.
            </div>
          )}

          {filtered.map((item) => {
            const isActive = item.holo_id === activeHoloId;
            return (
              <div
                key={item.holo_id}
                onClick={() => onSelectSnapshot(item.holo_id)}
                style={{
                  borderRadius: 6,
                  border: isActive
                    ? "1px solid #0ea5e9"
                    : "1px solid #e5e7eb",
                  padding: 6,
                  display: "flex",
                  flexDirection: "column",
                  gap: 3,
                  cursor: "pointer",
                  background: isActive ? "#e0f2fe" : "#ffffff",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 8,
                    alignItems: "baseline",
                  }}
                >
                  <div style={{ overflow: "hidden" }}>
                    <div
                      style={{
                        fontWeight: 600,
                        fontSize: 11,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                      title={item.holo_id}
                    >
                      {item.holo_id}
                    </div>
                    <div
                      style={{
                        fontSize: 10,
                        color: "#9ca3af",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                      title={item.path}
                    >
                      {item.path}
                    </div>
                  </div>

                  <div
                    style={{
                      fontSize: 10,
                      color: "#9ca3af",
                      whiteSpace: "nowrap",
                      textAlign: "right",
                    }}
                  >
                    {new Date(item.created_at).toLocaleString()}
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    fontSize: 10,
                    color: "#6b7280",
                    marginTop: 2,
                    flexWrap: "wrap",
                  }}
                >
                  <span>
                    mem={item.memory_seed_count ?? 0} · rules=
                    {item.rulebook_seed_count ?? 0}
                  </span>
                </div>

                {item.tags && item.tags.length > 0 && (
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 4,
                      marginTop: 2,
                    }}
                  >
                    {item.tags.slice(0, 6).map((t) => (
                      <span
                        key={t}
                        style={{
                          borderRadius: 999,
                          border: "1px solid #e5e7eb",
                          padding: "1px 6px",
                          fontSize: 9,
                          color: "#4b5563",
                          background: "#f9fafb",
                        }}
                      >
                        {t}
                      </span>
                    ))}
                    {item.tags.length > 6 && (
                      <span
                        style={{
                          fontSize: 9,
                          color: "#9ca3af",
                          marginLeft: 2,
                        }}
                      >
                        +{item.tags.length - 6} more
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}