// frontend/sci/pages/IDE.tsx
'use client';

import React, { useState } from "react";

// QFC loader (handles nodes/links/beams + sockets)
import QuantumFieldCanvasLoader from "../../components/Hologram/QuantumFieldCanvasLoader";

// SCI panel host (tabs for Editor / Atomsheet / Memory / SQS)
import SciPanelHost from "../../pages/sci/SciPanelHost";

// QFC focus context provider (required for useQFCFocus)
import { QFCFocusProvider } from "../../components/QuantumField/qfc_focus_context";

export default function IDE() {
  // Later you can read this from route/query, for now it's fine hard-coded
  const [containerId] = useState<string>("default");

  return (
    <div className="flex h-screen w-screen bg-black text-white">
      {/* Left: Quantum Field Canvas, wrapped in QFCFocusProvider */}
      <div className="flex-1 border-r border-zinc-800">
        <QFCFocusProvider>
          <QuantumFieldCanvasLoader containerId={containerId} />
        </QFCFocusProvider>
      </div>

      {/* Right: SCI Panels (Editor / Atomsheet / Memory / SQS) */}
      <div className="w-[420px] max-w-[480px] flex flex-col bg-zinc-950">
        <SciPanelHost containerId={containerId} />
      </div>
    </div>
  );
}