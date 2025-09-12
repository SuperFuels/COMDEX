// frontend/components/Hologram/HoverMemorySummary.tsx
import React from "react";
import { Html } from "@react-three/drei";

interface HoverMemorySummaryProps {
  position: [number, number, number];
  summary: string;
  containerId: string;
  agentId: string;
}

const HoverMemorySummary: React.FC<HoverMemorySummaryProps> = ({
  position,
  summary,
  containerId,
  agentId,
}) => {
  return (
    <Html position={position} center>
      <div className="max-w-xs p-2 rounded-xl shadow-xl bg-white/90 backdrop-blur text-xs text-black space-y-1">
        <div className="font-bold text-slate-800">🧠 Memory Summary</div>
        <div className="text-gray-700">{summary}</div>
        <div className="text-[10px] text-gray-500">Container: {containerId}</div>
        <div className="text-[10px] text-gray-500">Agent: {agentId}</div>
      </div>
    </Html>
  );
};

export default HoverMemorySummary;