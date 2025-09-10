// ✅ File: frontend/components/QuantumField/AtomView/atom_orbit_renderer.tsx

import React from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

interface OrbitLayerProps {
  radius: number;
  segments?: number;
  color?: string;
  opacity?: number;
  thickness?: number;
}

/**
 * 🔄 Renders a circular orbit layer around the nucleus.
 * Can be used to represent electron shells or energy levels.
 */
const OrbitLayer: React.FC<OrbitLayerProps> = ({
  radius,
  segments = 64,
  color = "#00ffff",
  opacity = 0.4,
  thickness = 1,
}) => {
  const points = React.useMemo(() => {
    const pts = [];
    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0));
    }
    return pts;
  }, [radius, segments]);

  const geometry = new THREE.BufferGeometry().setFromPoints(points);

  return (
    <line geometry={geometry}>
      <lineBasicMaterial
        attach="material"
        color={color}
        transparent
        opacity={opacity}
        linewidth={thickness}
      />
    </line>
  );
};

interface AtomNucleusProps {
  radius?: number;
  color?: string;
  glow?: boolean;
}

/**
 * ⚛️ Renders the central nucleus of the atom.
 */
const AtomNucleus: React.FC<AtomNucleusProps> = ({
  radius = 0.4,
  color = "#ffaa00",
  glow = true,
}) => {
  const material = new THREE.MeshBasicMaterial({ color });
  if (glow) material.emissive = new THREE.Color(color);

  return (
    <mesh position={[0, 0, 0]}>
      <sphereGeometry args={[radius, 32, 32]} />
      <meshBasicMaterial color={color} />
    </mesh>
  );
};

/**
 * 🔬 AtomView Component: nucleus + orbit layers.
 */
const AtomView: React.FC = () => {
  return (
    <group>
      <AtomNucleus />
      <OrbitLayer radius={1} />
      <OrbitLayer radius={2} color="#ff66ff" opacity={0.3} />
      <OrbitLayer radius={3} color="#66ff66" opacity={0.3} />
    </group>
  );
};

export default AtomView;