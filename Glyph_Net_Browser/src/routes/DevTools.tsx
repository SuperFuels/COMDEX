// Glyph_Net_Browser/src/routes/DevTools.tsx
// Dev Tools dashboard inside the Glyph Net browser.

import { useState, useEffect } from "react";
import PhotonEditor from "../components/PhotonEditor";
import LedgerInspector from "../components/LedgerInspector";
import PhotonGuide from "../components/PhotonGuide";
import DevPitch from "../components/DevPitch";

// 2D canvas (still useful as fallback / inspector)
import DevFieldCanvas from "../components/DevFieldCanvas";

// 3D hologram scene wrapper (Canvas + OrbitControls)
import DevFieldHologram3DContainer from "../components/DevFieldHologram3DContainer";

type ToolId = "editor" | "ledger" | "guide" | "pitch" | "field";

export default function DevTools() {
  const [activeTool, setActiveTool] = useState<ToolId>("editor");

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
      }

      if (target) setActiveTool(target);
    }

    window.addEventListener("devtools.switch_tab", handleSwitch as any);
    return () =>
      window.removeEventListener("devtools.switch_tab", handleSwitch as any);
  }, []);

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      {/* Header */}
      <header>
        <h1 style={{ marginBottom: 4 }}>Dev Tools</h1>
        <p
          style={{
            margin: 0,
            fontSize: 13,
            color: "#6b7280",
            maxWidth: 720,
          }}
        >
          Experimental dev dashboard wired directly into the Glyph Net browser.
        </p>
      </header>

      {/* Tool switcher */}
      <div
        style={{
          display: "inline-flex",
          borderRadius: 999,
          border: "1px solid #e5e7eb",
          background: "#f9fafb",
          padding: 4,
          gap: 4,
        }}
      >
        <ToolButton
          id="editor"
          label="Text Editor"
          description="Photon scratchpad (CRDT-backed)"
          activeTool={activeTool}
          onSelect={setActiveTool}
        />
        <ToolButton
          id="ledger"
          label="Ledger Inspector"
          description="View KG ledger entries (personal)"
          activeTool={activeTool}
          onSelect={setActiveTool}
        />
        <ToolButton
          id="guide"
          label="Language Guide"
          description=".ptn / .phn / .photon overview"
          activeTool={activeTool}
          onSelect={setActiveTool}
        />
        <ToolButton
          id="pitch"
          label="Why compress?"
          description="Developer pitch for glyph code/logs"
          activeTool={activeTool}
          onSelect={setActiveTool}
        />
        <ToolButton
          id="field"
          label="Field Lab"
          description="Live GHX / QField canvas (dev)"
          activeTool={activeTool}
          onSelect={setActiveTool}
        />
      </div>

      {/* Active tool card */}
      <section
        style={{
          flex: 1,
          borderRadius: 12,
          border: "1px solid #e5e7eb",
          background: "#f9fafb",
          padding: 16,
          overflow: "auto",
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
        ) : (
          // Swap this line if you want 2D vs 3D:
          // <DevFieldCanvas />
          <DevFieldHologram3DContainer />
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
        padding: "6px 12px",
        borderRadius: 999,
        cursor: "pointer",
        fontSize: 12,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        minWidth: 160,
        background: active ? "#0f172a" : "transparent",
        color: active ? "#e5e7eb" : "#111827",
        boxShadow: active ? "0 0 0 1px #0ea5e9 inset" : "none",
      }}
    >
      <span style={{ fontWeight: 600 }}>{label}</span>
      <span
        style={{
          fontSize: 11,
          opacity: 0.8,
        }}
      >
        {description}
      </span>
    </button>
  );
}