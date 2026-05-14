// Glyph_Net_Browser/src/components/SettingsPanel.tsx
import React from "react";
import BridgePanel from "../routes/BridgePanel"; // 👈 note: BridgePanel, not ../routes/Bridge

export default function SettingsPanel() {
  return (
    <div
      style={{
        height: "calc(100vh - 96px)",
        padding: 16,
        boxSizing: "border-box",
      }}
    >
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>
        Settings
      </h2>

      {/* Radio / Bridge section */}
      <section
        style={{
          marginTop: 8,
          padding: 12,
          borderRadius: 12,
          border: "1px solid #e5e7eb",
          background: "#fff",
        }}
      >
        <h3
          style={{
            fontSize: 14,
            fontWeight: 600,
            marginBottom: 8,
          }}
        >
          Radio / RF Bridge
        </h3>
        <BridgePanel />
      </section>
    </div>
  );
}