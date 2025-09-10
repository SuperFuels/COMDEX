import React, { useRef, useMemo } from "react";
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
 * Used for visualizing multi-reality logic paths in QFC.
 */
export const HolographicPathOverlay: React.FC<{ path: HolographicPath }> = ({ path }) => {
  const ref = useRef<THREE.Line>(null);
  const materialRef = useRef<THREE.LineBasicMaterial>(null);

  const baseOpacity = path.opacity ?? 0.4;
  const shimmerSpeed = path.shimmerSpeed ?? 2.5;

  // 🔁 Shimmer animation
  useFrame(({ clock }) => {
    if (materialRef.current && path.shimmer) {
      const t = clock.getElapsedTime();
      const pulse = 0.5 + 0.5 * Math.sin(t * shimmerSpeed);
      materialRef.current.opacity = baseOpacity * pulse;
    }
  });

  // 🧠 Memoized geometry
  const geometry = useMemo(() => {
    if (!path.points?.length) return new THREE.BufferGeometry();
    const pts = path.points.map(([x, y, z]) => new THREE.Vector3(x, y, z));
    return new THREE.BufferGeometry().setFromPoints(pts);
  }, [path.points]);

  return (
    <line
      ref={ref}
      geometry={geometry}
      visible={path.visible !== false}
      name={`holographic-path-${path.id}`}
    >
      <lineBasicMaterial
        ref={materialRef}
        color={path.color || "#00ffff"}
        linewidth={2}
        transparent
        opacity={baseOpacity}
        depthWrite={false}
      />
    </line>
  );
};