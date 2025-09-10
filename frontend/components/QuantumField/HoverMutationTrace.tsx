import React from "react";
import { Line } from "@react-three/drei";

interface HoverMutationTraceProps {
  trails: {
    path: [number, number, number][];
    isBreakthrough?: boolean;
    isDeadEnd?: boolean;
  }[];
  hoveredNodeId?: string;
}

const HoverMutationTrace: React.FC<HoverMutationTraceProps> = ({ trails, hoveredNodeId }) => {
  if (!hoveredNodeId || !trails?.length) return null;

  return (
    <>
      {trails.map((trail, i) => (
        <Line
          key={`hover-trail-${i}`}
          points={trail.path}
          color={
            trail.isBreakthrough
              ? "#00ffcc"
              : trail.isDeadEnd
              ? "#ff3366"
              : "#999999"
          }
          lineWidth={2}
          dashed
          dashSize={0.4}
          gapSize={0.2}
        />
      ))}
    </>
  );
};

export default HoverMutationTrace;