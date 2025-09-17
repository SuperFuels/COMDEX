// ✅ File: frontend/components/QuantumField/AtomView/atom_orbit_renderer.tsx
"use client";

import React from "react";
import * as THREE from "three";

interface OrbitLayerProps {
  radius: number;
  segments?: number;
  color?: string;
  opacity?: number;
  thickness?: number;
}

/**
 * 🔄 Renders a circular orbit layer around the nucleus (as a Three.js Line).
 * Uses <primitive> to avoid the DOM <line> type collision in TSX.
 */
const OrbitLayer: React.FC<OrbitLayerProps> = ({
  radius,
  segments = 64,
  color = "#00ffff",
  opacity = 0.4,
  thickness = 1,
}) => {
  const points = React.useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0));
    }
    return pts;
  }, [radius, segments]);

  const geometry = React.useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setFromPoints(points);
    return g;
  }, [points]);

  const material = React.useMemo(
    () =>
      new THREE.LineBasicMaterial({
        color: new THREE.Color(color),
        transparent: true,
        opacity,
        linewidth: thickness, // note: most WebGL implementations ignore linewidth
      }),
    [color, opacity, thickness]
  );

  const line = React.useMemo(() => new THREE.Line(geometry, material), [geometry, material]);

  React.useEffect(() => {
    return () => {
      geometry.dispose();
      material.dispose();
    };
  }, [geometry, material]);

  return <primitive object={line} />;
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
  return (
    <mesh position={[0, 0, 0]}>
      <sphereGeometry args={[radius, 32, 32]} />
      <meshStandardMaterial
        color={color}
        emissive={glow ? color : undefined}
        emissiveIntensity={glow ? 0.6 : 0}
        roughness={0.4}
        metalness={0.1}
      />
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