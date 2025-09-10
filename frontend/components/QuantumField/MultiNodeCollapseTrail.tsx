import React from "react";
import { Line } from "@react-three/drei";

interface CollapseTrailSegment {
  id: string;
  from: [number, number, number];
  to: [number, number, number];
  type?: string;
  strength?: number; // Optional SQI collapse strength
}

interface MultiNodeCollapseTrailProps {
  segments: CollapseTrailSegment[];
  visible?: boolean;
}

const getColorByType = (type: string = "") => {
  switch (type) {
    case "entangled":
      return "#00e0ff"; // cyan
    case "decay":
      return "#ff0055"; // red/pink
    case "cascade":
      return "#ffa500"; // orange
    default:
      return "#ffffff"; // white
  }
};

const MultiNodeCollapseTrail: React.FC<MultiNodeCollapseTrailProps> = ({ segments, visible = true }) => {
  if (!visible || segments.length === 0) return null;

  return (
    <>
      {segments.map((seg) => {
        const color = getColorByType(seg.type);
        const width = 0.15 + (seg.strength || 0) * 0.3; // thickness = base + collapse strength

        return (
          <Line
            key={seg.id}
            points={[seg.from, seg.to]}
            color={color}
            lineWidth={width}
            dashed={false}
            transparent
            opacity={0.8}
          />
        );
      })}
    </>
  );
};

export default MultiNodeCollapseTrail;