// ✅ File: frontend/components/QuantumField/AtomView/snap_to_energy_shells.tsx

import React from "react";
import * as THREE from "three";

/**
 * Calculates a snapped electron position to the nearest quantized energy shell.
 * Shells are concentric spheres around the origin (or nucleus) at fixed radii.
 */
export function snapToEnergyShell(
  position: [number, number, number],
  shellRadiusStep = 1.5,
  maxShells = 6
): [number, number, number] {
  const vec = new THREE.Vector3(...position);
  const distance = vec.length();

  // Find the nearest shell index (0-based)
  const shellIndex = Math.min(
    maxShells - 1,
    Math.round(distance / shellRadiusStep)
  );

  const snappedDistance = (shellIndex + 1) * shellRadiusStep;
  const snappedVec = vec.normalize().multiplyScalar(snappedDistance);

  return [snappedVec.x, snappedVec.y, snappedVec.z];
}

/**
 * Renders concentric wireframe spheres to indicate energy shells.
 */
export const EnergyShellRings: React.FC<{
  shellCount?: number;
  shellRadiusStep?: number;
  color?: string;
}> = ({ shellCount = 6, shellRadiusStep = 1.5, color = "#4444ff" }) => {
  const rings = [];
  for (let i = 1; i <= shellCount; i++) {
    const radius = i * shellRadiusStep;
    const geometry = new THREE.SphereGeometry(radius, 32, 32);
    const material = new THREE.MeshBasicMaterial({
      color,
      wireframe: true,
      transparent: true,
      opacity: 0.2,
    });
    rings.push(<primitive key={i} object={new THREE.Mesh(geometry, material)} />);
  }
  return <>{rings}</>;
};
