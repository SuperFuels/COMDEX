// ✅ File: frontend/components/QuantumField/Memory/memory_embedding_renderer.tsx

import React, { useMemo, useEffect } from "react";
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
  // Build geometry from points
  const geometry = useMemo(() => {
    const points = trace.tracePath.map(([x, y, z]) => new THREE.Vector3(x, y, z));
    return new THREE.BufferGeometry().setFromPoints(points);
  }, [trace.tracePath]);

  // Material (we'll animate its opacity)
  const material = useMemo(() => {
    const m = new THREE.LineBasicMaterial({
      color: new THREE.Color(trace.color ?? "#99ffcc"),
      transparent: true,
      opacity: trace.intensity ?? 0.6,
    });
    return m;
  }, [trace.color, trace.intensity]);

  // The actual three.js Line object
  const line = useMemo(() => new THREE.Line(geometry, material), [geometry, material]);

  // Animate material opacity (pulse)
  useFrame(({ clock }) => {
    const pulse = 0.4 + 0.4 * Math.sin(clock.getElapsedTime() * 2);
    material.opacity = (trace.intensity ?? 0.6) * pulse;
  });

  // Cleanup GPU resources when dependencies change/unmount
  useEffect(() => {
    return () => {
      geometry.dispose();
      material.dispose();
    };
  }, [geometry, material]);

  // Use <primitive> to avoid SVG <line> typing conflicts
  return <primitive object={line} />;
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