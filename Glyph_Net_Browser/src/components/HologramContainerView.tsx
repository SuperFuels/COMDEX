import { useEffect, useState } from "react";
import DevFieldHologram3DContainer from "./DevFieldHologram3DContainer";

import type { HoloIR } from "../lib/types/holo";
import type { HoloIndexEntry } from "../lib/api/holo";
import {
  fetchLatestHoloForContainer,
  listHolosForContainer,
  fetchHoloAtTick,
  exportHoloForContainer,
} from "../lib/api/holo";

export interface HologramContainerViewProps {
  containerId: string;
  title?: string;
  /** If you already know which holo to start with */
  initialHoloId?: string;
  /** Show the “Export .holo snapshot” button (default: true) */
  allowExport?: boolean;
}

/**
 * Generic container-level hologram view.
 *
 * Responsibilities:
 *  - Load latest Holo for a container
 *  - Load history (C1F index)
 *  - Allow selecting a specific snapshot
 *  - Render via DevFieldHologram3DContainer
 */
export default function HologramContainerView({
  containerId,
  title = "Hologram Container View",
  initialHoloId,
  allowExport = true,
}: HologramContainerViewProps) {
  const [holo, setHolo] = useState<HoloIR | null>(null);
  const [holoIndex, setHoloIndex] = useState<HoloIndexEntry[] | null>(null);
  const [loadingIndex, setLoadingIndex] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load latest holo (ignore initialHoloId for now)
  useEffect(() => {
    let cancelled = false;
    setError(null);

    fetchLatestHoloForContainer(containerId)
      .then((h) => {
        if (!cancelled) setHolo(h);
      })
      .catch(() => {
        if (!cancelled) setHolo(null);
      });

    return () => {
      cancelled = true;
    };
  }, [containerId]);

  // Load index (history) for this container
  useEffect(() => {
    let cancelled = false;
    setLoadingIndex(true);
    setError(null);

    listHolosForContainer(containerId)
      .then((entries) => {
        if (!cancelled) setHoloIndex(entries);
      })
      .catch((err: any) => {
        console.warn("[HologramContainerView] Failed to load holo index:", err);
        if (!cancelled) setHoloIndex(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingIndex(false);
      });

    return () => {
      cancelled = true;
    };
  }, [containerId]);

  async function handleExport() {
    setExporting(true);
    setError(null);

    const revisions =
      (holoIndex ?? [])
        .map((e) => e.revision ?? 0)
        .filter((n) => Number.isFinite(n)) as number[];

    const nextRevision =
      (revisions.length ? Math.max(...revisions) : 0) + 1;

    try {
      const snapshot = await exportHoloForContainer(
        containerId,
        {
          tick: 0,
          reason: "hologram_container_view_export",
          source_view: "qfc",
          frame: "mutated",
        },
        nextRevision,
      );

      setHolo(snapshot);

      // refresh index
      try {
        const entries = await listHolosForContainer(containerId);
        setHoloIndex(entries);
      } catch {
        // non-fatal
      }
    } catch (err: any) {
      console.error("[HologramContainerView] export failed:", err);
      setError(err?.message ?? "Holo export failed");
    } finally {
      setExporting(false);
    }
  }

  async function handleLoad(entry: HoloIndexEntry) {
    if (entry.tick == null || entry.revision == null) return;
    setError(null);

    try {
      const h = await fetchHoloAtTick(containerId, entry.tick, entry.revision);
      if (h) {
        setHolo(h);
      }
    } catch (err: any) {
      console.error("[HologramContainerView] load at tick failed:", err);
      setError(err?.message ?? "Failed to load holo snapshot");
    }
  }

  const snapshotCount = holoIndex?.length ?? 0;

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      {/* Compact header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          fontSize: 11,
          color: "#111827",
        }}
      >
        <span style={{ fontWeight: 600 }}>{title}</span>
        <span style={{ color: "#6b7280" }}>
          container: <code>{containerId}</code>
          {" · "}
          holo:{" "}
          {holo ? (
            <code>{holo.holo_id}</code>
          ) : (
            <span style={{ opacity: 0.7 }}>none</span>
          )}
        </span>
      </div>

      {/* Controls + history bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          borderRadius: 999,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: "4px 8px",
          fontSize: 11,
          color: "#6b7280",
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: 6,
          }}
        >
          <span style={{ fontWeight: 600, color: "#111827" }}>History</span>
          {loadingIndex ? (
            <span style={{ opacity: 0.7 }}>loading…</span>
          ) : !holoIndex || snapshotCount === 0 ? (
            <span style={{ opacity: 0.7 }}>no snapshots yet</span>
          ) : (
            holoIndex.map((entry) => {
              const label = `t=${entry.tick ?? "?"}/v=${
                entry.revision ?? "?"
              }`;
              const active = entry.holo_id === holo?.holo_id;
              return (
                <button
                  key={entry.holo_id}
                  type="button"
                  onClick={() => handleLoad(entry)}
                  style={{
                    padding: "2px 8px",
                    borderRadius: 999,
                    border: "1px solid #e5e7eb",
                    background: active ? "#0f172a" : "#f9fafb",
                    color: active ? "#e5e7eb" : "#111827",
                    cursor: "pointer",
                    fontSize: 10,
                  }}
                >
                  {label}
                </button>
              );
            })
          )}
          {snapshotCount > 0 && !loadingIndex && (
            <span style={{ fontSize: 10, opacity: 0.7 }}>
              {snapshotCount} snapshot{snapshotCount === 1 ? "" : "s"}
            </span>
          )}
        </div>

        {allowExport && (
          <button
            type="button"
            onClick={handleExport}
            disabled={exporting}
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #0f172a",
              background: exporting ? "#e5e7eb" : "#0f172a",
              color: exporting ? "#6b7280" : "#e5e7eb",
              cursor: exporting ? "default" : "pointer",
              fontSize: 11,
              fontWeight: 500,
              whiteSpace: "nowrap",
            }}
          >
            {exporting ? "Exporting…" : "Export .holo"}
          </button>
        )}
      </div>

      {error && (
        <div style={{ fontSize: 11, color: "#b91c1c" }}>{error}</div>
      )}

      {/* 3D field */}
      <div style={{ flex: 1, minHeight: 320 }}>
        <DevFieldHologram3DContainer holo={holo} />
      </div>
    </div>
  );
}