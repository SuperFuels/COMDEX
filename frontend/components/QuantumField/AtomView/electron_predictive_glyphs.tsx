// ✅ File: frontend/components/QuantumField/AtomView/electron_predictive_glyphs.tsx

import React, { useRef, useState } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";

export interface ElectronProps {
  id: string;
  position: [number, number, number];
  predictedGlyph?: string;
  hoverColor?: string;
  defaultColor?: string;
  onClick?: (id: string) => void;
}

/**
 * 🔮 ElectronSphere shows prediction glyphs on hover or click.
 */
export const ElectronSphere: React.FC<ElectronProps> = ({
  id,
  position,
  predictedGlyph,
  hoverColor = "#00ffff",
  defaultColor = "#ffffff",
  onClick,
}) => {
  const ref = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  useFrame(() => {
    if (ref.current) {
      ref.current.rotation.y += 0.01;
    }
  });

  return (
    <mesh
      ref={ref}
      position={position}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
      onClick={() => onClick?.(id)}
    >
      <sphereGeometry args={[0.2, 32, 32]} />
      <meshStandardMaterial color={hovered ? hoverColor : defaultColor} />

      {hovered && predictedGlyph && (
        <Html position={[0, 0.4, 0]} center distanceFactor={8} className="text-xs">
          <div className="bg-black/80 text-white px-2 py-1 rounded shadow">
            {predictedGlyph}
          </div>
        </Html>
      )}
    </mesh>
  );
};

/**
 * 🧪 Test wrapper for multiple electrons
 */
export const ElectronPredictionTest: React.FC = () => {
  const electrons: ElectronProps[] = [
    {
      id: "e1",
      position: [2, 0, 0],
      predictedGlyph: "⊕"
    },
    {
      id: "e2",
      position: [-2, 0, 0],
      predictedGlyph: "⧖"
    },
  ];

  return (
    <>
      {electrons.map((e) => (
        <ElectronSphere key={e.id} {...e} />
      ))}
    </>
  );
};
