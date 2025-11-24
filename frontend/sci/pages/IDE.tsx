// frontend/sci/pages/IDE.tsx
"use client";

import { useState } from "react";
import SciSqsPanel from "@/pages/sci/sci_sqs_panel";
import HolographicViewer from "@/components/Hologram/HolographicViewer";
import PhotonEditor from "@/components/PhotonEditor";

type ToolId = "editor" | "atomsheet" | "qfield";

const DEFAULT_CONTAINER = "backend/data/sheets/example_sheet.atom";

export default function SciIde() {
  const [activeTool, setActiveTool] = useState<ToolId>("editor"); // 👈 default = text editor
  const containerId = DEFAULT_CONTAINER;

  return (
    <div className="flex h-[calc(100vh-64px)] bg-black text-white">
      {/* Left sidebar: launcher */}
      <aside className="w-56 border-r border-slate-800 p-3 space-y-2">
        <SidebarButton
          active={activeTool === "editor"}
          label="Text Editor (.ptn)"
          onClick={() => setActiveTool("editor")}
        />
        <SidebarButton
          active={activeTool === "atomsheet"}
          label="AtomSheet (4D grid)"
          onClick={() => setActiveTool("atomsheet")}
        />
        <SidebarButton
          active={activeTool === "qfield"}
          label="Quantum Field Canvas"
          onClick={() => setActiveTool("qfield")}
        />

        {/* later: “New file”, “Open container”, etc. */}
      </aside>

      {/* Main workspace */}
      <main className="flex-1 relative overflow-hidden">
        {activeTool === "editor" && (
          <div className="h-full">
            {/* scratchpad for .ptn / raw text; docId can be anything stable */}
            <PhotonEditor docId="sci-main.ptn" />
          </div>
        )}

        {activeTool === "atomsheet" && (
          <div className="h-full overflow-auto">
            <SciSqsPanel containerId={containerId} file={containerId} />
          </div>
        )}

        {activeTool === "qfield" && (
          <div className="h-full">
            <HolographicViewer containerId={containerId} />
          </div>
        )}
      </main>
    </div>
  );
}

function SidebarButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left text-xs px-3 py-2 rounded-lg border transition
        ${active
          ? "bg-slate-900 border-cyan-400 text-cyan-100"
          : "bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700"}`}
    >
      {label}
    </button>
  );
}