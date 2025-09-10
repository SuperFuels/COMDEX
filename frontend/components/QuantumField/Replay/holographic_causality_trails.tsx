// ✅ File: frontend/components/QuantumField/Replay/holographic_causality_trails.tsx

import React, { useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

export interface CausalityTrailSegment {
  id: string;
  points: [number, number, number][];
  state?: "predicted" | "collapsed" | "contradicted";
  shimmer?: boolean;
  opacity?: number;
  color?: string;
}

const stateColorMap: Record<string, string> = {
  predicted: "#00ffff",      // Cyan shimmer
  collapsed: "#ffaa00",      // Golden orange
  contradicted: "#ff3355",   // Red-pink
};

const TrailLine: React.FC<{ segment: CausalityTrailSegment }> = ({ segment }) => {
  const ref = useRef<THREE.Line>(null);
  const materialRef = useRef<THREE.LineBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (materialRef.current && segment.shimmer) {
      const time = clock.getElapsedTime();
      const pulse = 0.4 + 0.4 * Math.sin(time * 2);
      materialRef.current.opacity = segment.opacity ?? pulse;
    }
  });

  const geometry = new THREE.BufferGeometry().setFromPoints(
    segment.points.map(([x, y, z]) => new THREE.Vector3(x, y, z))
  );

  return (
    <line ref={ref} geometry={geometry} visible>
      <lineBasicMaterial
        ref={materialRef}
        attach="material"
        color={segment.color || stateColorMap[segment.state || "predicted"]}
        transparent
        opacity={segment.opacity ?? 0.6}
        linewidth={2}
      />
    </line>
  );
};

const HolographicCausalityTrails: React.FC<{
  trails: CausalityTrailSegment[];
}> = ({ trails }) => {
  if (!trails?.length) return null;

  return (
    <>
      {trails.map((segment) => (
        <TrailLine key={segment.id} segment={segment} />
      ))}
    </>
  );
};

export default HolographicCausalityTrails;