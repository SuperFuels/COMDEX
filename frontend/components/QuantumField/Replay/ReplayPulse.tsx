// File: frontend/components/QuantumField/Replay/ReplayPulse.tsx
"use client";

import * as React from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

const ReplayPulse: React.FC<{ position: [number, number, number] }> = ({ position }) => {
  // loosen ref type to avoid @types/three vs three mismatch
  const pulseRef = React.useRef<any>(null);

  useFrame(({ clock }) => {
    const scale = 1 + Math.sin(clock.getElapsedTime() * 4) * 0.2;
    if (pulseRef.current) {
      (pulseRef.current as THREE.Mesh).scale.set(scale, scale, scale);
    }
  });

  return (
    <mesh
      position={position}
      // use callback ref instead of passing the RefObject directly
      ref={(node: any) => {
        pulseRef.current = node;
      }}
    >
      <ringGeometry args={[0.5, 0.6, 32]} />
      <meshBasicMaterial color="#00ffcc" transparent opacity={0.6} />
    </mesh>
  );
};

export default ReplayPulse;