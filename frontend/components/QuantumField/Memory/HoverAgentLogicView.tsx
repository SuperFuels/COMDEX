import React from "react";
import { Html } from "@react-three/drei";

interface HoverAgentLogicViewProps {
  position: [number, number, number];
  logicSummary: string;
  containerId?: string;
  agentId?: string;
}

const HoverAgentLogicView: React.FC<HoverAgentLogicViewProps> = ({
  position,
  logicSummary,
  containerId,
  agentId,
}) => {
  return (
    <Html
      position={position}
      center
      style={{
        background: "rgba(0,0,0,0.75)",
        padding: "0.6rem 0.8rem",
        borderRadius: "0.5rem",
        fontSize: "0.7rem",
        color: "#ffffff",
        whiteSpace: "pre-wrap",
        maxWidth: 240,
        pointerEvents: "none",
        fontFamily: "monospace",
        boxShadow: "0 0 8px rgba(0,0,0,0.5)",
      }}
    >
      <div>
        <strong>🧠 Symbolic Memory</strong>
        <div className="mt-1">{logicSummary}</div>
        {containerId && (
          <div className="mt-1 text-xs opacity-80">
            📦 Container: <span className="font-mono">{containerId}</span>
          </div>
        )}
        {agentId && (
          <div className="text-xs opacity-80">
            🤖 Agent: <span className="font-mono">{agentId}</span>
          </div>
        )}
      </div>
    </Html>
  );
};

export default HoverAgentLogicView;