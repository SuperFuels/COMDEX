// ✅ File: frontend/components/QuantumField/AtomView/memory_echo_beams.tsx

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
 * 🔁 Memory Echo Beams — represents symbolic memory traces around atoms.
 * Visualized as expanding and fading ring pulses around a center.
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

const EchoRing: React.FC<MemoryEcho> = ({ center, radius, color = "#00ffff", pulse = true, intensity = 1 }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.MeshBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (!pulse || !meshRef.current || !materialRef.current) return;
    const t = clock.getElapsedTime();
    const scale = 1 + 0.5 * Math.sin(t * 2);
    meshRef.current.scale.set(scale, scale, scale);
    materialRef.current.opacity = 0.3 + 0.3 * Math.sin(t * 2);
  });

  const ringGeometry = new THREE.RingGeometry(radius * 0.9, radius, 32);

  return (
    <mesh ref={meshRef} position={new THREE.Vector3(...center)} rotation={[-Math.PI / 2, 0, 0]}>
      <ringGeometry args={[radius * 0.9, radius, 32]} />
      <meshBasicMaterial
        ref={materialRef}
        color={color}
        transparent
        opacity={0.5 * intensity}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
};

export default MemoryEchoBeams;