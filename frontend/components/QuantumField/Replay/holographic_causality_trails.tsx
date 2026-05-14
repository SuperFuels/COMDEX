// ✅ File: frontend/components/QuantumField/Replay/holographic_causality_trails.tsx
import React, { useEffect, useMemo, useRef } from "react";
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

const stateColorMap: Record<NonNullable<CausalityTrailSegment["state"]>, string> = {
  predicted: "#00ffff",    // Cyan shimmer
  collapsed: "#ffaa00",    // Golden orange
  contradicted: "#ff3355", // Red-pink
};

function TrailLine({ segment }: { segment: CausalityTrailSegment }) {
  // Geometry + material are real Three objects. We render them via <primitive>
  const geometryRef = useRef(new THREE.BufferGeometry());
  const material = useMemo(
    () =>
      new THREE.LineBasicMaterial({
        color: segment.color || stateColorMap[segment.state ?? "predicted"],
        transparent: true,
        opacity: segment.opacity ?? 0.6,
        linewidth: 2, // has effect on some platforms; fine to set
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [segment.color, segment.state] // opacity may animate below
  );

  // Build/update the geometry when points change
  useEffect(() => {
    const pts = segment.points.map(([x, y, z]) => new THREE.Vector3(x, y, z));
    geometryRef.current.setFromPoints(pts);
  }, [segment.points]);

  // Animate shimmer by modulating opacity
  useFrame(({ clock }) => {
    if (!segment.shimmer) return;
    const t = clock.getElapsedTime();
    const pulse = 0.4 + 0.4 * Math.sin(t * 2);
    material.opacity = segment.opacity ?? pulse;
  });

  // Clean up
  useEffect(() => {
    return () => {
      geometryRef.current.dispose();
      material.dispose();
    };
  }, [material]);

  // Create the line object once and re-use it
  const lineObject = useMemo(
    () => new THREE.Line(geometryRef.current, material),
    [material]
  );

  return <primitive object={lineObject} />;
}

const HolographicCausalityTrails: React.FC<{ trails: CausalityTrailSegment[] }> = ({
  trails,
}) => {
  if (!trails || trails.length === 0) return null;
  return (
    <>
      {trails.map((segment) => (
        <TrailLine key={segment.id} segment={segment} />
      ))}
    </>
  );
};

export default HolographicCausalityTrails;