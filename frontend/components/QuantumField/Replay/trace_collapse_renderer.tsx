// frontend/components/QuantumField/Replay/trace_collapse_renderer.tsx
"use client";

import React, { useMemo, useEffect } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

/** One shimmering line built from a list of 3D points */
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
  width?: number;          // note: linewidth is largely ignored by WebGLRenderer, but kept for completeness
  animate?: boolean;
  baseOpacity?: number;
  shimmerSpeed?: number;
}) => {
  // Geometry from the provided points
  const geometry = useMemo(() => {
    const verts = points.map((p) => new THREE.Vector3(p[0], p[1], p[2]));
    const g = new THREE.BufferGeometry();
    g.setFromPoints(verts);
    return g;
  }, [points]);

  // Basic line material (transparent so we can animate opacity)
  const material = useMemo(
    () =>
      new THREE.LineBasicMaterial({
        color: new THREE.Color(color),
        transparent: true,
        opacity: baseOpacity,
        depthWrite: false,
        linewidth: width, // will be ignored by most platforms but typed correctly
      }),
    [color, baseOpacity, width]
  );

  // The actual Three.js object
  const line = useMemo(() => new THREE.Line(geometry, material), [geometry, material]);

  // Animate a subtle shimmer by modulating opacity
  useFrame(({ clock }) => {
    if (!animate) return;
    const t = clock.getElapsedTime();
    const shimmer = 0.5 + 0.5 * Math.sin(t * shimmerSpeed);
    material.opacity = baseOpacity * shimmer;
  });

  // Clean up GPU resources on unmount
  useEffect(() => {
    return () => {
      geometry.dispose();
      material.dispose();
    };
  }, [geometry, material]);

  // Render as a primitive to avoid DOM/SVG typing collisions
  return <primitive object={line} />;
};

/** Renders multiple collapse trails */
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
          color={trail.color ?? color}
          animate={trail.animate ?? animate}
        />
      ))}
    </>
  );
};

export default TraceCollapseRenderer;