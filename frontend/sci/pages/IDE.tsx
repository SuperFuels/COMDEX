// IDE.tsx
import React, { useState } from "react";
import QuantumFieldCanvasLoader from "../../components/Hologram/QuantumFieldCanvasLoader";
import SciPanelHost from "../../pages/sci/SciPanelHost";

export default function IDE() {
  // later: you can take this from route/query instead of hardcoding
  const [containerId] = useState<string>("default");

  return (
    <div className="flex h-screen w-screen bg-black text-white">
      {/* Left: Quantum Field Canvas */}
      <div className="flex-1 border-r border-zinc-800">
        <QuantumFieldCanvasLoader containerId={containerId} />
      </div>

      {/* Right: SCI Panels (Editor / Atomsheet / Memory / SQS) */}
      <div className="w-[420px] max-w-[480px] flex flex-col bg-zinc-950">
        <SciPanelHost />
        {/* if you later want panels to be container-aware:
            <SciPanelHost containerId={containerId} />
        */}
      </div>
    </div>
  );
}