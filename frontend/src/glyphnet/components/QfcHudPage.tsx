// Glyph_Net_Browser/src/components/QfcHudPage.tsx
"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useTessarisTelemetry } from "../hooks/useTessarisTelemetry";
import { QFCHudPanel } from "../routes/DevTools";

type ToolId =
  | "editor"
  | "ledger"
  | "guide"
  | "pitch"
  | "field"
  | "qfc"
  | "qfc_bio"
  | "aion"
  | "crystal"
  | "gma"
  | "gma_auth"
  | "docs";

/**
 * QFC HUD (PHYS) standalone page.
 * Uses the SAME dashboard + DevField/QFCViewport stack as DevTools.
 */
export default function QfcHudPage() {
  const telemetry = useTessarisTelemetry();
  const [containerId, setContainerId] = useState<string>("dc_aion_core");

  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const cid = params.get("container") || params.get("containerId") || "dc_aion_core";
      setContainerId(cid);
    } catch {
      setContainerId("dc_aion_core");
    }
  }, []);

  // preserve querystring (container, etc.)
  const qs = typeof window !== "undefined" ? window.location.search : "";
  const withQS = useMemo(() => (path: string) => (qs ? `${path}${qs}` : path), [qs]);

  const navHash = (path: string) => {
    const p = path.startsWith("/") ? path : `/${path}`;
    const target = withQS(p);

    // if the app is hash-routed, drive hash
    if (typeof window !== "undefined" && window.location.hash && window.location.hash.startsWith("#")) {
      window.location.hash = p;
      return;
    }

    // otherwise use normal navigation
    if (typeof window !== "undefined") window.location.href = target;
  };

  // force active state so the pill highlights on the PHYS HUD page:
  const activeTool: ToolId = "qfc";

  return (
    <div
      style={{
        minHeight: "100vh", // ✅ fixes “compressed/no height”
        display: "flex",
        flexDirection: "column",
        padding: 12, // ✅ consistent alignment with other pages
      }}
    >
      <section
        style={{
          flex: 1, // ✅ lets HUD take full remaining height
          minHeight: 0,
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#f9fafb",
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        {/* Header + tool pills (matches DevTools header style) */}
        <header
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#111827" }}>Dev Tools</div>
          </div>

          <div
            style={{
              display: "inline-flex",
              flexWrap: "wrap",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#ffffff",
              padding: 2,
              gap: 2,
            }}
          >
            <ToolButton id="editor" label="Text Editor" description="Photon scratchpad" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="ledger" label="Ledger" description="KG ledger entries" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="guide" label="Language" description=".ptn / .phn / .photon" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="pitch" label="Why compress?" description="Dev pitch" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="field" label="Field Lab" description="GHX / QField canvas" activeTool={activeTool} onSelect={() => navHash("/devtools")} />

            <ToolButton id="qfc" label="QFC HUD" description="Scenario HUD + knobs" activeTool={activeTool} onSelect={() => navHash("/qfc-hud")} />
            <ToolButton id="qfc_bio" label="QFC Bio" description="Biology-focused HUD" activeTool={activeTool} onSelect={() => navHash("/qfc-bio")} />

            <ToolButton id="aion" label="AION Memory" description="Internal holo seeds" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="crystal" label="Crystals" description="Compressed motifs" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="gma" label="GMA" description="Monetary state (dev)" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="gma_auth" label="GMA" description="Monetary authority" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="docs" label="Docs" description="Transactable docs" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
          </div>
        </header>

        {/* HUD body */}
        <div style={{ flex: 1, minHeight: 0 }}>
          <QFCHudPanel
            containerId={containerId}
            telemetry={telemetry}
            urlPrefix=""
            defaultScenario="BG01"
            domainLabel="PHYS"
            // leave variant default for PHYS (this includes the dashboard)
          />
        </div>
      </section>
    </div>
  );
}

function ToolButton({
  id,
  label,
  description,
  activeTool,
  onSelect,
}: {
  id: ToolId;
  label: string;
  description: string;
  activeTool: ToolId;
  onSelect: () => void;
}) {
  const active = activeTool === id;

  return (
    <button
      type="button"
      onClick={onSelect}
      style={{
        border: 0,
        cursor: "pointer",
        borderRadius: 999,
        padding: "8px 10px",
        background: active ? "#0b1220" : "transparent",
        color: active ? "#ffffff" : "#111827",
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "flex-start",
        gap: 1,
        minWidth: 110,
      }}
    >
      <div style={{ fontSize: 12, fontWeight: 700, lineHeight: 1 }}>{label}</div>
      <div
        style={{
          fontSize: 10,
          lineHeight: 1,
          opacity: active ? 0.85 : 0.65,
          whiteSpace: "nowrap",
        }}
      >
        {description}
      </div>
    </button>
  );
}