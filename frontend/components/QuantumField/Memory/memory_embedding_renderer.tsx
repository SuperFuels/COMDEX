// ✅ File: frontend/components/QuantumField/Memory/memory_embedding_renderer.tsx

import React from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

export interface MemoryEmbedding {
  id: string;
  tracePath: [number, number, number][];
  intensity?: number;
  age?: number;
  color?: string;
}

const MemoryTraceLine: React.FC<{ trace: MemoryEmbedding }> = ({ trace }) => {
  const ref = React.useRef<THREE.Line>(null);
  const materialRef = React.useRef<THREE.LineBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (materialRef.current) {
      const pulse = 0.4 + 0.4 * Math.sin(clock.getElapsedTime() * 2);
      materialRef.current.opacity = (trace.intensity ?? 0.6) * pulse;
    }
  });

  const geometry = new THREE.BufferGeometry().setFromPoints(
    trace.tracePath.map(([x, y, z]) => new THREE.Vector3(x, y, z))
  );

  return (
    <line ref={ref} geometry={geometry} visible>
      <lineBasicMaterial
        ref={materialRef}
        attach="material"
        color={trace.color || "#99ffcc"}
        transparent
        opacity={trace.intensity ?? 0.6}
        linewidth={2}
      />
    </line>
  );
};

const MemoryEmbeddingRenderer: React.FC<{ embeddings: MemoryEmbedding[] }> = ({ embeddings }) => {
  return (
    <>
      {embeddings.map((trace) => (
        <MemoryTraceLine key={trace.id} trace={trace} />
      ))}
    </>
  );
};

export default MemoryEmbeddingRenderer;
