// ✅ Q6a: Knowledge Node Placement — File: knowledge_node_renderer.tsx

import React from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

export interface KnowledgeNodeProps {
  id: string;
  position: [number, number, number];
  label: string;
  color?: string;
  pulsing?: boolean;
}

const KnowledgeNode: React.FC<KnowledgeNodeProps> = ({ id, position, label, color = "#4ade80", pulsing }) => {
  const meshRef = React.useRef<THREE.Mesh>(null);
  const materialRef = React.useRef<THREE.MeshStandardMaterial>(null);

  useFrame(({ clock }) => {
    if (materialRef.current && pulsing) {
      const time = clock.getElapsedTime();
      const intensity = 0.5 + 0.5 * Math.sin(time * 2);
      materialRef.current.emissiveIntensity = intensity;
    }
  });

  return (
    <mesh ref={meshRef} position={position}>
      <sphereGeometry args={[0.25, 16, 16]} />
      <meshStandardMaterial
        ref={materialRef}
        color={color}
        emissive={color}
        emissiveIntensity={pulsing ? 1 : 0.3}
        transparent
        opacity={0.9}
      />
      {/* 🧠 Optional: label rendering here if needed */}
    </mesh>
  );
};

export default KnowledgeNode;