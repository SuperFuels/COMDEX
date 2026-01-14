// Glyph_Net_Browser/src/components/HologramContainerView.tsx
import { useEffect, useState } from "react";
import DevFieldHologram3DContainer from "./DevFieldHologram3DContainer";
import { PhotonStubPanel } from "./PhotonStubPanel";

import type { HoloIR } from "../lib/types/holo";
import type { HoloIndexItem } from "../lib/api/holo";
import {
  fetchLatestHoloForContainer,
  listHolosForContainer,
  fetchHoloAtTick,
  exportHoloForContainer,
} from "../lib/api/holo";
import { buildPhotonStubFromHolo, buildGhxFromHolo } from "../lib/rehydrate";

type HologramContainerViewProps = {
  containerId: string;
  title?: string;
  /** If you already know which holo to start with */
  initialHoloId?: string;
  /** Show the “Export .holo snapshot” button (default: true) */
  allowExport?: boolean;

  // 🔁 Optional overrides coming from DevTools
  holo?: HoloIR | null;
  holoFiles?: HoloIndexItem[];
  onSelectHolo?: (item: HoloIndexItem) => void;
};

/**
 * Generic container-level hologram view.
 *
 * Responsibilities:
 *  - Load latest Holo for a container
 *  - Load history (index)
 *  - Allow selecting a specific snapshot
 *  - Render via DevFieldHologram3DContainer
 *  - Rehydrate .holo back into the live Field Lab
 */
export default function HologramContainerView({
  containerId,
  title = "Hologram Container View",
  initialHoloId,
  allowExport = true,
  holo: holoProp,
  holoFiles,
  onSelectHolo,
}: HologramContainerViewProps) {
  const [holo, setHolo] = useState<HoloIR | null>(holoProp ?? null);
  const [holoIndex, setHoloIndex] = useState<HoloIndexItem[] | null>(null);
  const [loadingIndex, setLoadingIndex] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // keep local holo in sync with prop when DevTools passes one in
  useEffect(() => {
    if (holoProp !== undefined) {
      setHolo(holoProp ?? null);
    }
  }, [holoProp]);

  // Latest holo for this container (ignores initialHoloId for now)
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
  }, [containerId, initialHoloId]);

  // Index (history) for this container
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

  // React to devtools.holo_saved (e.g. program builder → .holo import)
  useEffect(() => {
    function handleSaved(ev: Event) {
      const detail = (ev as CustomEvent).detail as { holo?: HoloIR } | undefined;
      if (!detail?.holo) return;

      if (detail.holo.container_id === containerId) {
        listHolosForContainer(containerId)
          .then(setHoloIndex)
          .catch(() => {
            /* non-fatal */
          });
      }
    }

    if (typeof window === "undefined") return;

    window.addEventListener("devtools.holo_saved", handleSaved as any);
    return () => {
      window.removeEventListener("devtools.holo_saved", handleSaved as any);
    };
  }, [containerId]);

  async function handleExport() {
    setExporting(true);
    setError(null);

    const revisions =
      (holoIndex ?? [])
        .map((e) => e.revision ?? 0)
        .filter((n) => Number.isFinite(n)) as number[];

    const nextRevision = (revisions.length ? Math.max(...revisions) : 0) + 1;

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

      try {
        const entries = await listHolosForContainer(containerId);
        setHoloIndex(entries);
      } catch {
        /* non-fatal */
      }
    } catch (err: any) {
      console.error("[HologramContainerView] export failed:", err);
      setError(err?.message ?? "Holo export failed");
    } finally {
      setExporting(false);
    }
  }

  async function handleLoad(entry: HoloIndexItem) {
    if (entry.tick == null || entry.revision == null) return;
    setError(null);

    try {
      const h = await fetchHoloAtTick(containerId, entry.tick, entry.revision);
      if (h) setHolo(h);
    } catch (err: any) {
      console.error("[HologramContainerView] load at tick failed:", err);
      setError(err?.message ?? "Failed to load holo snapshot");
    }
  }

  // Rehydrate this container's .holo back into the live Field Lab
  function handleRehydrateToField() {
    if (!holo) return;
    if (typeof window === "undefined") return;

    const packet = buildGhxFromHolo(holo);

    (window as any).__DEVTOOLS_LAST_GHX = packet;

    window.dispatchEvent(
      new CustomEvent("devtools.ghx", {
        detail: { ghx: packet },
      }),
    );

    window.dispatchEvent(
      new CustomEvent("devtools.switch_tab", {
        detail: { tool: "field" },
      }),
    );
  }

  const snapshotCount = holoIndex?.length ?? 0;
  const photonStub = holo ? buildPhotonStubFromHolo(holo) : null;

  // Source for the left “Holo Files” cabinet:
  const cabinetFiles: HoloIndexItem[] = holoFiles ?? holoIndex ?? [];

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
              const label = `t=${entry.tick ?? "?"}/v=${entry.revision ?? "?"}`;
              const active = entry.holo_id === holo?.holo_id;
              return (
                <button
                  key={`${entry.tick}-${entry.revision}-${entry.holo_id}`}
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

        <div
          style={{
            display: "flex",
            gap: 6,
            alignItems: "center",
            flexShrink: 0,
          }}
        >
          <button
            type="button"
            onClick={handleRehydrateToField}
            disabled={!holo}
            style={{
              padding: "3px 8px",
              borderRadius: 999,
              border: "1px solid #22c55e",
              background: holo ? "#16a34a" : "#e5e7eb",
              color: holo ? "#ecfdf5" : "#6b7280",
              cursor: holo ? "pointer" : "default",
              fontSize: 10,
              fontWeight: 500,
              whiteSpace: "nowrap",
            }}
          >
            ↻ Rehydrate to Field
          </button>

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
      </div>

      {error && (
        <div style={{ fontSize: 11, color: "#b91c1c" }}>{error}</div>
      )}

      {/* Main body: left Holo Files cabinet + right 3D field */}
      <div
        style={{
          flex: 1,
          display: "flex",
          gap: 12,
          minHeight: 320,
        }}
      >
        {/* Left column: Holo Files cabinet */}
        <div
          style={{
            borderRadius: 12,
            border: "1px solid #e5e7eb",
            background: "#ffffff",
            padding: 12,
            fontSize: 12,
            display: "flex",
            flexDirection: "column",
            minWidth: 220,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Holo Files</div>

          {/* Program files (primary) */}
          <ul
            style={{
              listStyle: "none",
              margin: 0,
              padding: 0,
              marginBottom: 8,
              paddingBottom: 6,
              borderBottom: "1px solid #e5e7eb",
              fontSize: 11,
              color: "#111827",
            }}
          >
            {["main.holo", "loop.holo", "exec.holo", "output.holo"].map(
              (name, idx) => {
                const rowBg =
                  idx % 2 === 0 ? "transparent" : "rgba(15,23,42,0.02)";
                return (
                  <li key={name}>
                    <div
                      style={{
                        width: "100%",
                        padding: "4px 6px",
                        borderRadius: 6,
                        background: rowBg,
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <span>{name}</span>
                      <span style={{ fontSize: 10, color: "#9ca3af" }}>
                        file
                      </span>
                    </div>
                  </li>
                );
              },
            )}
          </ul>

          {/* Snapshots from backend index (secondary) */}
          <div
            style={{
              fontSize: 10,
              textTransform: "uppercase",
              letterSpacing: 0.04,
              color: "#9ca3af",
              marginBottom: 4,
            }}
          >
            Snapshots
          </div>

          {!holoFiles || holoFiles.length === 0 ? (
            <div style={{ fontSize: 11, color: "#9ca3af" }}>
              no snapshots yet
            </div>
          ) : (
            <ul
              style={{
                listStyle: "none",
                margin: 0,
                padding: 0,
                flex: 1,
                overflowY: "auto",
              }}
            >
              {holoFiles.map((hf, idx) => {
                const label = `t=${hf.tick ?? 0} · v${hf.revision ?? 1}`;
                const rowBg =
                  idx % 2 === 0 ? "transparent" : "rgba(15,23,42,0.02)";
                return (
                  <li key={`${hf.tick}-${hf.revision}`}>
                    <button
                      type="button"
                      onClick={() => onSelectHolo && onSelectHolo(hf)}
                      style={{
                        width: "100%",
                        textAlign: "left",
                        padding: "4px 6px",
                        borderRadius: 6,
                        border: "none",
                        background: rowBg,
                        cursor: "pointer",
                        fontSize: 11,
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <span>{label}</span>
                      <span style={{ fontSize: 10, color: "#6b7280" }}>
                        v{hf.revision ?? "?"}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Right column: 3D field */}
        <div style={{ flex: 1, minHeight: 320 }}>
          <DevFieldHologram3DContainer
            holo={holo}
            mode="field"
            allowExternalGhx
          />
        </div>
      </div>

      {/* Photon motif stub row */}
      {photonStub && (
        <div
          style={{
            marginTop: 8,
            display: "flex",
            gap: 12,
            alignItems: "flex-start",
          }}
        >
          <div
            style={{
              flex: 1,
              borderRadius: 12,
              border: "1px solid #020617",
              background: "#020617",
              padding: 8,
            }}
          >
            <div
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: "#e5e7eb",
                marginBottom: 4,
              }}
            >
              Photon motif stub
            </div>

            <div
              style={{
                fontSize: 10,
                color: "#9ca3af",
                marginBottom: 6,
                maxWidth: 720,
              }}
            >
              Generated from the current <code>.holo</code> snapshot. Use{" "}
              <b>“Send to Text Editor”</b> to edit this motif in Photon, then
              run your normal <b>Photon → Hologram</b> flow to regenerate a new
              hologram / <code>.holo</code>.
            </div>

            <div
              style={{
                maxHeight: 260,
                overflow: "auto",
              }}
            >
              <PhotonStubPanel code={photonStub} />
            </div>
          </div>

          {/* Spacer to match 3D inspector width */}
          <div style={{ width: 320 }} />
        </div>
      )}
    </div>
  );
}