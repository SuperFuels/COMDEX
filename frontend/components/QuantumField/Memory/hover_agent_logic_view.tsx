// ✅ File: frontend/components/QuantumField/Memory/hover_agent_logic_view.tsx

import React from "react";
import { Html } from "@react-three/drei";
import { cn } from "@/lib/utils";

export interface HoverLogicProps {
  agentName: string;
  containerId: string;
  logicSummary: string;
  tick?: number;
  position: [number, number, number];
  visible: boolean;
}

/**
 * 🧠 Displays symbolic memory logic from a past container or agent state.
 * Rendered as floating HTML tooltip in 3D space.
 */
const HoverAgentLogicView: React.FC<HoverLogicProps> = ({
  agentName,
  containerId,
  logicSummary,
  tick,
  position,
  visible,
}) => {
  if (!visible) return null;

  return (
    <Html position={position} center distanceFactor={10} occlude>
      <div
        className={cn(
          "bg-black/80 text-white text-xs p-3 rounded-lg border border-white/20 shadow-xl max-w-xs backdrop-blur-sm",
          "transition-opacity duration-300"
        )}
      >
        <div className="text-sm font-bold text-indigo-300">🧠 {agentName}</div>
        <div className="text-white/80">{logicSummary}</div>
        <div className="mt-1 text-[10px] text-white/50">
          Container: <strong>{containerId}</strong>
          {tick !== undefined && (
            <>
              , Tick: <strong>{tick}</strong>
            </>
          )}
        </div>
      </div>
    </Html>
  );
};

export default HoverAgentLogicView;