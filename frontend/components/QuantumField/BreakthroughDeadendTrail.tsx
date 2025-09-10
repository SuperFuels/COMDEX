import React from "react";
import { Line } from "@react-three/drei";

interface TrailSegment {
  points: [number, number, number][];
  type: "deadend" | "breakthrough";
  label?: string;
}

interface BreakthroughDeadendTrailProps {
  segments: TrailSegment[];
  visible?: boolean;
}

const colorMap = {
  deadend: "#ef4444",       // red
  breakthrough: "#10b981",  // emerald green
};

export default function BreakthroughDeadendTrail({
  segments,
  visible = true,
}: BreakthroughDeadendTrailProps) {
  if (!visible) return null;

  return (
    <>
      {segments.map((seg, i) => (
        <Line
          key={`trail-${i}`}
          points={seg.points}
          color={colorMap[seg.type] || "#999"}
          lineWidth={2}
          dashed={false}
        />
      ))}
    </>
  );
}