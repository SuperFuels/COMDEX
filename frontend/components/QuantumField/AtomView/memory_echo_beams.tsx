// ✅ File: frontend/components/QuantumField/AtomView/memory_echo_beams.tsx
"use client";

import React, { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

export interface MemoryEcho {
  id: string;
  center: [number, number, number];
  radius: number;
  color?: string;
  pulse?: boolean;
  intensity?: number;
}

/**
 * 🔁 Memory Echo Beams — symbolic memory traces around atoms.
 * Expanding / fading ring pulses around a center.
 */
const MemoryEchoBeams: React.FC<{ echoes: MemoryEcho[] }> = ({ echoes }) => {
  return (
    <>
      {echoes.map((echo) => (
        <EchoRing key={echo.id} {...echo} />
      ))}
    </>
  );
};

const EchoRing: React.FC<MemoryEcho> = ({
  center,
  radius,
  color = "#00ffff",
  pulse = true,
  intensity = 1,
}) => {
  // loosen refs + use callback refs to avoid @types/three version clashes
  const meshRef = useRef<any>(null);
  const materialRef = useRef<any>(null);

  useFrame(({ clock }) => {
    if (!pulse || !meshRef.current || !materialRef.current) return;
    const t = clock.getElapsedTime();

    const scale = 1 + 0.5 * Math.sin(t * 2);
    meshRef.current.scale.set(scale, scale, scale);

    materialRef.current.opacity = 0.3 + 0.3 * Math.sin(t * 2);
  });

  return (
    <mesh
      ref={(node: any) => {
        meshRef.current = node;
      }}
      // use tuple position, not THREE.Vector3, to dodge Vector3 type mismatch
      position={center}
      rotation={[-Math.PI / 2, 0, 0]}
    >
      <ringGeometry args={[radius * 0.9, radius, 32]} />
      <meshBasicMaterial
        ref={(node: any) => {
          materialRef.current = node;
        }}
        color={color}
        transparent
        opacity={0.5 * intensity}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
};

export default MemoryEchoBeams;