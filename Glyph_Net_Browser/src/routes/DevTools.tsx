// Glyph_Net_Browser/src/routes/DevTools.tsx
// Dev Tools dashboard inside the Glyph Net browser.

import { useState, useEffect } from "react";
import PhotonEditor from "../components/PhotonEditor";
import LedgerInspector from "../components/LedgerInspector";
import PhotonGuide from "../components/PhotonGuide";
import DevPitch from "../components/DevPitch";
import AionMemoryFieldPanel from "../components/AionMemoryFieldPanel";
import CrystalPanel from "../components/CrystalPanel";

// 3D hologram scene wrapper (Canvas + OrbitControls)
import HologramContainerView from "../components/HologramContainerView";

// Hologram IR + API
import type { HoloIR } from "../lib/types/holo";
import {
  exportHoloForContainer,
  fetchLatestHoloForContainer,
  listHolosForContainer,
  fetchHoloAtTick,
} from "../lib/api/holo";
import type { HoloIndexEntry } from "../lib/api/holo";

type ToolId =
  | "editor"
  | "ledger"
  | "guide"
  | "pitch"
  | "field"
  | "aion"
  | "crystal";

export default function DevTools() {
  const [activeTool, setActiveTool] = useState<ToolId>("editor");

  // 🔭 Holo / container state
  const [activeContainerId, setActiveContainerId] = useState<string | null>(
    null,
  );
  const [holo, setHolo] = useState<HoloIR | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // 📚 Holo index (history)
  const [holoIndex, setHoloIndex] = useState<HoloIndexEntry[] | null>(null);
  const [loadingIndex, setLoadingIndex] = useState(false);

  // 👁️‍🗨️ Derive active container id from URL query (?container=dc_xxx)
  // Fallback for now is dc_aion_core (matches existing .dc.json + exports)
  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const cid =
        params.get("container") ||
        params.get("containerId") ||
        "dc_aion_core";
      setActiveContainerId(cid);
    } catch {
      // non-browser env / SSR safe no-op
      setActiveContainerId("dc_aion_core");
    }
  }, []);

  // 🔁 On container change, try to load the latest .holo snapshot (if any)
  useEffect(() => {
    if (!activeContainerId) {
      setHolo(null);
      return;
    }

    let cancelled = false;

    fetchLatestHoloForContainer(activeContainerId)
      .then((h) => {
        if (!cancelled) setHolo(h);
      })
      .catch(() => {
        // no holo yet (404) is fine – just clear state
        if (!cancelled) setHolo(null);
      });

    return () => {
      cancelled = true;
    };
  }, [activeContainerId]);

  // 📚 Load holo index whenever container changes
  useEffect(() => {
    if (!activeContainerId) {
      setHoloIndex(null);
      return;
    }

    let cancelled = false;
    setLoadingIndex(true);

    listHolosForContainer(activeContainerId)
      .then((entries) => {
        if (!cancelled) setHoloIndex(entries);
      })
      .catch(() => {
        if (!cancelled) setHoloIndex(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingIndex(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeContainerId]);

  // 👂 listen for global tab-switch events (from PhotonEditor, etc.)
  useEffect(() => {
    function handleSwitch(ev: Event) {
      const detail = (ev as CustomEvent).detail || {};

      // Preferred: detail.tool is one of our ToolId values
      let target: ToolId | undefined = detail.tool;

      // Fallback mapping if something sends { tab: "field-lab" } etc.
      if (!target && detail.tab) {
        if (detail.tab === "field-lab") target = "field";
        if (detail.tab === "editor") target = "editor";
        if (detail.tab === "ledger") target = "ledger";
        if (detail.tab === "language") target = "guide";
        if (detail.tab === "pitch") target = "pitch";
        if (detail.tab === "aion") target = "aion";
        if (detail.tab === "crystal") target = "crystal";
      }

      if (target) setActiveTool(target);
    }

    window.addEventListener("devtools.switch_tab", handleSwitch as any);
    return () =>
      window.removeEventListener("devtools.switch_tab", handleSwitch as any);
  }, []);

  async function handleExportHolo() {
    if (!activeContainerId) return;
    setExporting(true);
    setExportError(null);

    // 🔢 Figure out next revision number for this container
    const revisions =
      (holoIndex ?? [])
        .map((e) => e.revision ?? 0)
        .filter((n) => Number.isFinite(n)) as number[];

    const nextRevision =
      (revisions.length ? Math.max(...revisions) : 0) + 1;

    try {
      const snapshot = await exportHoloForContainer(
        activeContainerId,
        {
          tick: 0, // manual DevTools snapshots all at tick 0 for now
          reason: "devtools_manual_export",
          source_view: "qfc",
          frame: "mutated",
        },
        nextRevision, // 👈 key change: pass revision
      );

      setHolo(snapshot);
      console.info(
        "[DevTools] Holo exported:",
        snapshot.holo_id,
        "rev=",
        nextRevision,
      );

      // Refresh index after export so history shows new snapshot
      try {
        const entries = await listHolosForContainer(activeContainerId);
        setHoloIndex(entries);
      } catch {
        // non-fatal
      }
    } catch (err: any) {
      console.error("[DevTools] Holo export failed:", err);
      setExportError(err?.message ?? "Holo export failed");
    } finally {
      setExporting(false);
    }
  }

  async function handleLoadHoloAt(entry: HoloIndexEntry) {
    if (!activeContainerId) return;
    if (entry.tick == null || entry.revision == null) return;

    setExportError(null);
    try {
      const h = await fetchHoloAtTick(
        activeContainerId,
        entry.tick,
        entry.revision,
      );
      if (h) {
        setHolo(h);
        console.info(
          "[DevTools] Loaded holo snapshot:",
          h.holo_id,
          "tick=",
          entry.tick,
          "rev=",
          entry.revision,
        );
      }
    } catch (err: any) {
      console.error("[DevTools] Failed to load holo at tick:", err);
      setExportError(err?.message ?? "Failed to load holo snapshot");
    }
  }

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      {/* Header – compact */}
      <header
        style={{
          marginBottom: 4,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
        }}
      >
        <div
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "#111827",
          }}
        >
          Dev Tools
        </div>

        {activeTool === "field" && (
          <div
            style={{
              fontSize: 11,
              color: "#9ca3af",
            }}
          >
            {activeContainerId && (
              <>
                container: <code>{activeContainerId}</code>
                {" · "}
              </>
            )}
            holo:{" "}
            {holo ? (
              <code>{holo.holo_id}</code>
            ) : (
              <span style={{ opacity: 0.7 }}>none</span>
            )}
          </div>
        )}
      </header>

      {/* Tool switcher + (optional) field status */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <div
          style={{
            display: "inline-flex",
            flexWrap: "wrap",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            background: "#f9fafb",
            padding: 2,
            gap: 2,
          }}
        >
          <ToolButton
            id="editor"
            label="Text Editor"
            description="Photon scratchpad"
            activeTool={activeTool}
            onSelect={setActiveTool}
          />
          <ToolButton
            id="ledger"
            label="Ledger"
            description="KG ledger entries"
            activeTool={activeTool}
            onSelect={setActiveTool}
          />
          <ToolButton
            id="guide"
            label="Language"
            description=".ptn / .phn / .photon"
            activeTool={activeTool}
            onSelect={setActiveTool}
          />
          <ToolButton
            id="pitch"
            label="Why compress?"
            description="Dev pitch"
            activeTool={activeTool}
            onSelect={setActiveTool}
          />
          <ToolButton
            id="field"
            label="Field Lab"
            description="GHX / QField canvas"
            activeTool={activeTool}
            onSelect={setActiveTool}
          />
          <ToolButton
            id="aion"
            label="AION Memory"
            description="Internal holo seeds"
            activeTool={activeTool}
            onSelect={setActiveTool}
          />
          <ToolButton
            id="crystal"
            label="Crystals"
            description="Compressed motifs"
            activeTool={activeTool}
            onSelect={setActiveTool}
          />
        </div>

        {activeTool === "field" && (
          <div
            style={{
              fontSize: 11,
              color: "#6b7280",
              display: "flex",
              alignItems: "center",
              gap: 6,
              whiteSpace: "nowrap",
            }}
          >
            {activeContainerId && (
              <>
                <span>
                  container: <code>{activeContainerId}</code>
                </span>
                <span>·</span>
              </>
            )}
            <span>
              holo:{" "}
              {holo ? (
                <code>{holo.holo_id}</code>
              ) : (
                <span style={{ opacity: 0.7 }}>none</span>
              )}
            </span>
          </div>
        )}
      </div>

      {/* Active tool card */}
      <section
        style={{
          flex: 1,
          borderRadius: 12,
          border: "1px solid #e5e7eb",
          background: "#f9fafb",
          padding: 12,
          overflow: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {activeTool === "editor" ? (
          <PhotonEditor docId="devtools" />
        ) : activeTool === "ledger" ? (
          <LedgerInspector />
        ) : activeTool === "guide" ? (
          <PhotonGuide />
        ) : activeTool === "pitch" ? (
          <DevPitch />
        ) : activeTool === "aion" ? (
          <AionMemoryFieldPanel />
        ) : activeTool === "crystal" ? (
          <CrystalPanel />
        ) : (
          // Field Lab: generic HologramContainerView
          <div style={{ flex: 1, minHeight: 320 }}>
            <HologramContainerView
              containerId={activeContainerId ?? "dc_aion_core"}
              title="Hologram Container"
            />
          </div>
        )}

        {exportError && activeTool === "field" && (
          <div style={{ fontSize: 11, color: "#b91c1c" }}>{exportError}</div>
        )}

        {activeTool === "field" && (
          <div
            style={{
              marginTop: 8,
              display: "flex",
              justifyContent: "flex-end",
            }}
          >
            <button
              type="button"
              onClick={handleExportHolo}
              disabled={exporting || !activeContainerId}
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
          </div>
        )}
      </section>
    </div>
  );
}

type ToolButtonProps = {
  id: ToolId;
  label: string;
  description: string;
  activeTool: ToolId;
  onSelect: (id: ToolId) => void;
};

function ToolButton({
  id,
  label,
  description,
  activeTool,
  onSelect,
}: ToolButtonProps) {
  const active = activeTool === id;
  return (
    <button
      type="button"
      onClick={() => onSelect(id)}
      style={{
        border: "none",
        padding: "4px 10px", // smaller
        borderRadius: 999,
        cursor: "pointer",
        fontSize: 11, // smaller
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        minWidth: 120, // less wide
        background: active ? "#0f172a" : "transparent",
        color: active ? "#e5e7eb" : "#111827",
        boxShadow: active ? "0 0 0 1px #0ea5e9 inset" : "none",
      }}
    >
      <span style={{ fontWeight: 600 }}>{label}</span>
      <span
        style={{
          fontSize: 10,
          opacity: 0.8,
        }}
      >
        {description}
      </span>
    </button>
  );
}