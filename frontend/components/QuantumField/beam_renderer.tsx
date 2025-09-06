// File: frontend/components/QuantumField/beam_renderer.tsx

import * as THREE from "three";
import React, { useRef } from "react";
import { useFrame } from "@react-three/fiber";

export interface BeamProps {
  source: [number, number, number];
  target: [number, number, number];
  prediction?: boolean;
  collapseState?: "collapsed" | "predicted" | "contradicted";
  sqiScore?: number;
  show?: boolean; // optional overlay toggle
}

export const QWaveBeam: React.FC<BeamProps> = ({
  source,
  target,
  prediction = false,
  collapseState,
  sqiScore = 0,
  show = true,
}) => {
  const materialRef = useRef<THREE.MeshStandardMaterial>(null);
  const beamRef = useRef<THREE.Mesh>(null);
  const pulse = useRef(0);

  if (!show) return null;

  // 🎯 Beam path: smooth curved tube
  const curve = new THREE.QuadraticBezierCurve3(
    new THREE.Vector3(...source),
    new THREE.Vector3(
      (source[0] + target[0]) / 2,
      (source[1] + target[1]) / 2 + 1.5,
      (source[2] + target[2]) / 2
    ),
    new THREE.Vector3(...target)
  );
  const points = curve.getPoints(32);
  const geometry = new THREE.TubeGeometry(
    new THREE.CatmullRomCurve3(points),
    32,
    0.06,
    8,
    false
  );

  // 🎨 Beam color logic
  const getBeamColor = () => {
    if (collapseState === "contradicted") return "#ff3333";
    if (collapseState === "collapsed") return "#00ffee";
    if (prediction) return "#ffff00";
    return "#aaaaff";
  };

  // 💡 Glow logic
  useFrame(() => {
    pulse.current += 0.02;
    const oscillation = 0.5 + 0.5 * Math.sin(pulse.current);
    if (materialRef.current) {
      materialRef.current.emissiveIntensity = 0.6 + oscillation * sqiScore * 2;
      materialRef.current.opacity = 0.7 + 0.3 * oscillation;
    }
  });

  return (
    <mesh geometry={geometry} ref={beamRef}>
      <meshStandardMaterial
        ref={materialRef}
        color={getBeamColor()}
        emissive={getBeamColor()}
        transparent
        opacity={0.9}
        emissiveIntensity={1}
      />
    </mesh>
  );
};