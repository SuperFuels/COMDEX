// Glyph_Net_Browser/src/routes/DevTools.tsx
// Dev Tools dashboard inside the Glyph Net browser.

import { useState } from "react";
import PhotonEditor from "../components/PhotonEditor";
import LedgerInspector from "../components/LedgerInspector";

type ToolId = "editor" | "ledger";

export default function DevTools() {
  const [activeTool, setActiveTool] = useState<ToolId>("editor");

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
          Select a tool below. The Photon text editor is a local scratchpad; the
          Ledger Inspector walks the KG ledger over the HTTP API.
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
      </div>

      {/* Active tool card */}
      <section
        style={{
          flex: 1,
          borderRadius: 12,
          border: "1px solid #e5e7eb",
          // OLD: background: "#020617",
          background: "#f9fafb",        // 👈 light background
          padding: 16,
          overflow: "auto",
        }}
      >
        {activeTool === "editor" ? (
          <PhotonEditor docId="devtools" />
        ) : (
          <LedgerInspector />
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
        minWidth: 140,
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