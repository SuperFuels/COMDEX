// frontend/components/Hologram/HoverMutationTrace.tsx
"use client";

import React, { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

type Vec3 = [number, number, number];

interface Trail {
  path: Vec3[];
  isBreakthrough?: boolean;
  isDeadEnd?: boolean;
}

interface HoverMutationTraceProps {
  trails: Trail[];
  hoveredNodeId?: string;
}

/** Lightweight line helper (no drei types). Supports dashed lines. */
function SimpleLine({
  points,
  color = "#999999",
  opacity = 1,
  dashed = true,
  dashSize = 0.4,
  gapSize = 0.2,
}: {
  points: Vec3[];
  color?: string;
  opacity?: number;
  dashed?: boolean;
  dashSize?: number;
  gapSize?: number;
}) {
  const lineRef = useRef<THREE.Line | null>(null);

  // Positions buffer for the line
  const positionArray = useMemo(() => {
    const arr = new Float32Array(points.length * 3);
    points.forEach((p, i) => {
      arr[i * 3 + 0] = p[0];
      arr[i * 3 + 1] = p[1];
      arr[i * 3 + 2] = p[2];
    });
    return arr;
  }, [points]);

  // Compute line distances so dashes render correctly
  useEffect(() => {
    if (!lineRef.current) return;
    const geom = lineRef.current.geometry as THREE.BufferGeometry;
    // manual lineDistance calculation (works like geometry.computeLineDistances())
    const distances = new Float32Array(points.length);
    let acc = 0;
    for (let i = 0; i < points.length; i++) {
      if (i > 0) {
        const a = points[i - 1];
        const b = points[i];
        const dx = b[0] - a[0];
        const dy = b[1] - a[1];
        const dz = b[2] - a[2];
        acc += Math.sqrt(dx * dx + dy * dy + dz * dz);
      }
      distances[i] = acc;
    }
    geom.setAttribute("lineDistance", new THREE.BufferAttribute(distances, 1));
    geom.attributes.lineDistance.needsUpdate = true;
  }, [points]);

  return (
    <line ref={lineRef as any}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          array={positionArray}
          count={points.length}
          itemSize={3}
        />
      </bufferGeometry>
      {dashed ? (
        <lineDashedMaterial
          color={color}
          transparent
          opacity={opacity}
          dashSize={dashSize}
          gapSize={gapSize}
        />
      ) : (
        <lineBasicMaterial color={color} transparent opacity={opacity} />
      )}
    </line>
  );
}

const HoverMutationTrace: React.FC<HoverMutationTraceProps> = ({
  trails,
  hoveredNodeId,
}) => {
  if (!hoveredNodeId || !trails?.length) return null;

  return (
    <>
      {trails.map((trail, i) => (
        <SimpleLine
          key={`hover-trail-${i}`}
          points={trail.path}
          color={
            trail.isBreakthrough
              ? "#00ffcc"
              : trail.isDeadEnd
              ? "#ff3366"
              : "#999999"
          }
          dashed
          dashSize={0.4}
          gapSize={0.2}
          opacity={1}
        />
      ))}
    </>
  );
};

export default HoverMutationTrace;