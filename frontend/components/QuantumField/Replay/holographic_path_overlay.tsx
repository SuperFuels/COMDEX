// frontend/components/QuantumField/Replay/holographic_path_overlay.tsx
import React, { useRef, useMemo, useEffect } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

export interface HolographicPath {
  id: string;
  points: [number, number, number][];
  color?: string;
  visible?: boolean;
  shimmer?: boolean;
  opacity?: number;
  shimmerSpeed?: number; // 🌠 optional speed of shimmer
  glowIntensity?: number; // 💡 placeholder for future glowing upgrades
}

/**
 * 🌀 Renders a holographic path overlay representing a forked or collapsed trail.
 * NOTE: We use <primitive> with a THREE.Line to avoid the SVG <line> typing conflict.
 */
export const HolographicPathOverlay: React.FC<{ path: HolographicPath }> = ({ path }) => {
  const materialRef = useRef<THREE.LineBasicMaterial | null>(null);

  const baseOpacity = path.opacity ?? 0.4;
  const shimmerSpeed = path.shimmerSpeed ?? 2.5;

  // Build THREE objects once per relevant change
  const lineObject = useMemo(() => {
    const pts =
      (path.points ?? []).map(([x, y, z]) => new THREE.Vector3(x, y, z));

    const geom = new THREE.BufferGeometry().setFromPoints(pts);

    const mat = new THREE.LineBasicMaterial({
      color: new THREE.Color(path.color ?? "#00ffff"),
      linewidth: 2,
      transparent: true,
      opacity: baseOpacity,
      depthWrite: false,
    });
    materialRef.current = mat;

    const line = new THREE.Line(geom, mat);
    line.visible = path.visible !== false;
    line.name = `holographic-path-${path.id}`;
    return line;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path.id, path.points, path.color, baseOpacity, path.visible]);

  // Keep material color/opacity/visibility in sync with prop changes
  useEffect(() => {
    materialRef.current?.color.set(path.color ?? "#00ffff");
  }, [path.color]);

  useEffect(() => {
    if (materialRef.current) materialRef.current.opacity = baseOpacity;
  }, [baseOpacity]);

  useEffect(() => {
    if (lineObject) lineObject.visible = path.visible !== false;
  }, [lineObject, path.visible]);

  // 🔁 Shimmer animation
  useFrame(({ clock }) => {
    if (materialRef.current && path.shimmer) {
      const t = clock.getElapsedTime();
      const pulse = 0.5 + 0.5 * Math.sin(t * shimmerSpeed);
      materialRef.current.opacity = baseOpacity * pulse;
    }
  });

  if (!lineObject) return null;
  return <primitive object={lineObject} />;
};