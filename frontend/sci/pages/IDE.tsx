// frontend/sci/pages/IDE.tsx
'use client';

import React, { useState } from "react";
import dynamic from "next/dynamic";
import SciPanelHost from "../../pages/sci/SciPanelHost";
import { QFCFocusProvider } from "../../components/QuantumField/qfc_focus_context";

const QuantumFieldCanvasLoader = dynamic(
  () => import("../../components/Hologram/QuantumFieldCanvasLoader"),
  { ssr: false }
);

export default function IDE() {
  const [containerId] = useState<string>("default");

  return (
    <QFCFocusProvider>
      <div className="flex h-screen w-screen bg-black text-white">
        <div className="flex-1 border-r border-zinc-800">
          <QuantumFieldCanvasLoader containerId={containerId} />
        </div>

        <div className="w-[420px] max-w-[480px] flex flex-col bg-zinc-950">
          <SciPanelHost containerId={containerId} />
        </div>
      </div>
    </QFCFocusProvider>
  );
}