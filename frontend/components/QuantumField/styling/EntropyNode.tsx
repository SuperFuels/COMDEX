import React from "react";
import * as THREE from "three";
import { Html } from "@react-three/drei";

export interface EntropyNodeProps {
  position: [number, number, number];
  entropy: number; // 0 to 3.0 typically
  nodeId?: string;
}

// 🎨 Map entropy to a color gradient
const getEntropyColor = (entropy: number): string => {
  if (entropy < 0.5) return "#00ffaa"; // low entropy (stable)
  if (entropy < 1.5) return "#ffff00"; // medium
  if (entropy < 2.5) return "#ff8800"; // high
  return "#ff3333"; // max chaos
};

const EntropyNode: React.FC<EntropyNodeProps> = ({ position, entropy, nodeId }) => {
  const color = getEntropyColor(entropy);

  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[0.12, 16, 16]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={1.2} />
      </mesh>
      {nodeId && (
        <Html distanceFactor={10} position={[0, 0.3, 0]}>
          <div className="text-xs text-white bg-black/80 rounded px-1 py-0.5 shadow">
            ✨ {entropy.toFixed(2)}
          </div>
        </Html>
      )}
    </group>
  );
};

export default EntropyNode;
