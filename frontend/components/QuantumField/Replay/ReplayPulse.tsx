// File: frontend/components/QuantumField/Replay/ReplayPulse.tsx
import * as React from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

const ReplayPulse: React.FC<{ position: [number, number, number] }> = ({ position }) => {
  const pulseRef = React.useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    const scale = 1 + Math.sin(clock.getElapsedTime() * 4) * 0.2;
    if (pulseRef.current) {
      pulseRef.current.scale.set(scale, scale, scale);
    }
  });

  return (
    <mesh position={position} ref={pulseRef}>
      <ringGeometry args={[0.5, 0.6, 32]} />
      <meshBasicMaterial color="#00ffcc" transparent opacity={0.6} />
    </mesh>
  );
};

export default ReplayPulse;