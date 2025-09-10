// ✅ File: frontend/components/QuantumField/highlighted_symbolic_operators.tsx

import React from "react";
import * as THREE from "three";
import { Html } from "@react-three/drei";

interface HighlightedOperatorProps {
  position: [number, number, number];
  operator: string;
}

const operatorStyles: Record<string, { color: string; glow: string }> = {
  "⧖": { color: "#00ffff", glow: "#ccffff" }, // Time
  "↔": { color: "#ffff00", glow: "#ffffaa" }, // Bidirectional
  "⬁": { color: "#ff00ff", glow: "#ffccff" }, // Infinite loop
  "🧬": { color: "#00ff00", glow: "#aaffaa" }, // DNA/Mutation
  "🪞": { color: "#ff9900", glow: "#ffd580" }, // Mirror/Reflection
};

export const HighlightedOperator: React.FC<HighlightedOperatorProps> = ({
  position,
  operator,
}) => {
  const style = operatorStyles[operator] || {
    color: "#ffffff",
    glow: "#cccccc",
  };

  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[0.15, 16, 16]} />
        <meshStandardMaterial
          color={style.color}
          emissive={style.glow}
          emissiveIntensity={2}
        />
      </mesh>
      <Html>
        <div
          style={{
            color: style.color,
            textShadow: `0 0 6px ${style.glow}`,
            fontWeight: "bold",
            fontSize: "1.2rem",
          }}
        >
          {operator}
        </div>
      </Html>
    </group>
  );
};
