// frontend/components/QuantumField/MultiNodeCollapseTrail.tsx
import React from "react";

/** Basic vec3 tuple */
type Vec3 = [number, number, number];

interface CollapseTrailSegment {
  id: string;
  from: Vec3;
  to: Vec3;
  type?: "entangled" | "decay" | "cascade" | string;
  /** Optional SQI collapse strength (0..1) used for opacity accenting */
  strength?: number;
}

interface MultiNodeCollapseTrailProps {
  segments: CollapseTrailSegment[];
  visible?: boolean;
}

/** Tiny raw line helper to avoid drei <Line> typing/derivatives requirements */
const SimpleLine: React.FC<{
  from: Vec3;
  to: Vec3;
  color?: string;
  opacity?: number;
}> = ({ from, to, color = "#ffffff", opacity = 0.8 }) => {
  // Standard WebGL lines ignore thickness (linewidth) in most browsers.
  // If you need thick lines later, switch to three-stdlib Line2.
  return (
    <line>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={2}
          itemSize={3}
          array={new Float32Array([...from, ...to])}
        />
      </bufferGeometry>
      <lineBasicMaterial color={color} transparent opacity={opacity} />
    </line>
  );
};

const colorByType = (type?: string) => {
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

const MultiNodeCollapseTrail: React.FC<MultiNodeCollapseTrailProps> = ({
  segments,
  visible = true,
}) => {
  if (!visible || !segments?.length) return null;

  return (
    <>
      {segments.map((seg) => {
        const color = colorByType(seg.type);
        // Emphasize stronger collapses with a bit more opacity.
        const opacity = Math.min(1, 0.5 + (seg.strength ?? 0) * 0.5);

        return (
          <SimpleLine
            key={seg.id}
            from={seg.from}
            to={seg.to}
            color={color}
            opacity={opacity}
          />
        );
      })}
    </>
  );
};

export default MultiNodeCollapseTrail;