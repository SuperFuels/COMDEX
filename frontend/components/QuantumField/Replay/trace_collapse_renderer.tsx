import React, { useRef, useMemo } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

// 🌀 Holographic collapse trail line
const CollapseTraceLine = ({
  points,
  color = "#00ffff",
  width = 2,
  animate = true,
  baseOpacity = 0.6,
  shimmerSpeed = 2.5,
}: {
  points: [number, number, number][];
  color?: string;
  width?: number;
  animate?: boolean;
  baseOpacity?: number;
  shimmerSpeed?: number;
}) => {
  const lineRef = useRef<THREE.Line>(null);
  const materialRef = useRef<THREE.LineBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (animate && materialRef.current) {
      const time = clock.getElapsedTime();
      const shimmer = 0.5 + 0.5 * Math.sin(time * shimmerSpeed);
      materialRef.current.opacity = baseOpacity * shimmer;
    }
  });

  const geometry = useMemo(() => {
    const vecs = points.map((p) => new THREE.Vector3(...p));
    return new THREE.BufferGeometry().setFromPoints(vecs);
  }, [points]);

  return (
    <line ref={lineRef} geometry={geometry}>
      <lineBasicMaterial
        ref={materialRef}
        color={color}
        transparent
        opacity={baseOpacity}
        linewidth={width}
        depthWrite={false}
      />
    </line>
  );
};

// 🧠 Collapse trail renderer for multi-path logic traces
const TraceCollapseRenderer = ({
  trails,
  color = "#00ffff",
  animate = true,
}: {
  trails: {
    id: string;
    path: [number, number, number][];
    color?: string;
    animate?: boolean;
  }[];
  color?: string;
  animate?: boolean;
}) => {
  return (
    <>
      {trails.map((trail) => (
        <CollapseTraceLine
          key={trail.id}
          points={trail.path}
          color={trail.color || color}
          animate={trail.animate ?? animate}
        />
      ))}
    </>
  );
};

export default TraceCollapseRenderer;