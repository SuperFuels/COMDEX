// components/QuantumField/Node.tsx
import React, { useRef, useEffect, useState } from "react";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { GlyphNode } from "@/types/qfc";

type NodeProps = {
  node: GlyphNode;
  onTeleport?: (id: string) => void;
  predictedMode?: boolean;
  highlight?: boolean; // ✅ NEW
};

export const Node: React.FC<NodeProps> = ({
  node,
  onTeleport,
  predictedMode = false,
  highlight = false,
}) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const handleClick = () => {
    if (onTeleport) onTeleport(node.containerId || node.id);
  };

  const actualColor = node.locked ? "#ff3333" : node.color || "#00ffcc";
  const baseEmissive = node.locked ? "#ff3333" : "#000000";
  const defaultIntensity = node.locked ? 2.0 : 0;

  // 🌟 Animation effect for highlight + hover
  useEffect(() => {
    if (!meshRef.current) return;

    const mesh = meshRef.current;
    let frameId: number;
    let pulse = 0;

    const animate = () => {
      if (highlight) {
        pulse += 0.1;
        const scale = 1 + 0.1 * Math.sin(pulse);
        mesh.scale.set(scale, scale, scale);
      } else if (hovered) {
        mesh.rotation.y += 0.01;
      }
      frameId = requestAnimationFrame(animate);
    };

    animate();

    return () => cancelAnimationFrame(frameId);
  }, [highlight, hovered]);

  return (
    <>
      <mesh
        ref={meshRef}
        position={node.position}
        onClick={handleClick}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[0.5, 24, 24]} />
        <meshStandardMaterial
          color={highlight ? "#fff933" : actualColor}
          emissive={highlight ? "#fff933" : baseEmissive}
          emissiveIntensity={highlight ? 2.0 : defaultIntensity}
          opacity={predictedMode ? 0.15 : 1}
          transparent
        />
      </mesh>

      {/* 🔮 Dream-Origin Marker */}
      {node.source === "dream" && (
        <mesh position={node.position}>
          <ringGeometry args={[0.6, 0.75, 32]} />
          <meshBasicMaterial color="#d946ef" transparent opacity={0.75} />
        </mesh>
      )}
    </>
  );
};