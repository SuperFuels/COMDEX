// components/QuantumField/Node.tsx
import React, { useRef, useEffect, useState } from "react";
import * as THREE from "three";
import type { GlyphNode as BaseGlyphNode } from "@/types/qfc";

/**
 * Extend the upstream QFC GlyphNode with fields that may be present at runtime
 * but aren't declared in the base type. All extensions are optional to keep
 * this component tolerant to different payload shapes.
 */
type ViewGlyphNode = BaseGlyphNode & {
  id: string;
  position: [number, number, number] | THREE.Vector3;
  containerId?: string;
  source?: string;         // e.g. "dream"
  locked?: boolean;        // runtime flag
  color?: string;          // runtime color override
};

type NodeProps = {
  node: ViewGlyphNode;
  onTeleport?: (id: string) => void;
  predictedMode?: boolean;
  highlight?: boolean;
};

export const Node: React.FC<NodeProps> = ({
  node,
  onTeleport,
  predictedMode = false,
  highlight = false,
}) => {
  // loosen the type; we’ll wire it in via a callback ref
  const meshRef = useRef<THREE.Mesh | null>(null);
  const [hovered, setHovered] = useState(false);

  const handleClick = () => {
    const targetId = node.containerId ?? node.id;
    if (onTeleport) onTeleport(targetId);
  };

  const isLocked = Boolean(node.locked);
  const actualColor = node.color ?? (isLocked ? "#ff3333" : "#00ffcc");
  const baseEmissive = isLocked ? "#ff3333" : "#000000";
  const defaultIntensity = isLocked ? 2.0 : 0;

  // Animate highlight pulse or subtle hover spin
  useEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;

    let frameId = 0;
    let t = 0;

    const animate = () => {
      if (highlight) {
        t += 0.1;
        const s = 1 + 0.1 * Math.sin(t);
        mesh.scale.set(s, s, s);
      } else if (hovered) {
        mesh.rotation.y += 0.01;
      }
      frameId = requestAnimationFrame(animate);
    };

    frameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameId);
  }, [highlight, hovered]);

  // Normalize position for r3f <mesh position={...}>
  const position: [number, number, number] =
    node.position instanceof THREE.Vector3
      ? [node.position.x, node.position.y, node.position.z]
      : node.position;

  return (
    <>
      <mesh
        // callback ref avoids the @types/three vs three Mesh type mismatch
        ref={(el: any) => {
          meshRef.current = el as THREE.Mesh | null;
        }}
        position={position}
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
        <mesh position={position}>
          <ringGeometry args={[0.6, 0.75, 32]} />
          <meshBasicMaterial color="#d946ef" transparent opacity={0.75} />
        </mesh>
      )}
    </>
  );
};

export default Node;