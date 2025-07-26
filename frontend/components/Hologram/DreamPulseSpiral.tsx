import React, { useEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import * as THREE from "three";

interface DreamPulseSpiralProps {
  glyphs: string[];
  spiralRadius?: number;
  spiralHeight?: number;
  pulseSpeed?: number;
}

export default function DreamPulseSpiral({
  glyphs,
  spiralRadius = 2.0,
  spiralHeight = 4.0,
  pulseSpeed = 1.0
}: DreamPulseSpiralProps) {
  const spiralGroup = useRef<THREE.Group>(null);
  const pulseRef = useRef<number>(0);

  useFrame((_, delta) => {
    pulseRef.current += delta * pulseSpeed;
    if (spiralGroup.current) {
      spiralGroup.current.rotation.y += 0.002;
    }
  });

  const stepAngle = (2 * Math.PI) / Math.max(glyphs.length, 1);
  const stepHeight = spiralHeight / Math.max(glyphs.length, 1);

  return (
    <group ref={spiralGroup}>
      {glyphs.map((glyph, i) => {
        const angle = i * stepAngle;
        const height = i * stepHeight;
        const x = spiralRadius * Math.cos(angle);
        const z = spiralRadius * Math.sin(angle);
        const pulse = 0.5 + 0.5 * Math.sin(pulseRef.current - i * 0.3);
        const color = getDreamColor(glyph, pulse);
        return (
          <Text
            key={i}
            position={[x, height, z]}
            fontSize={0.12}
            color={color}
            anchorX="center"
            anchorY="middle"
            outlineWidth={0.003}
            outlineColor="#000000"
          >
            {glyph}
          </Text>
        );
      })}
    </group>
  );
}

function getDreamColor(glyph: string, pulse: number): string {
  if (glyph === "⧖" || glyph === "⬁") return `hsl(${Math.floor(pulse * 280)}, 100%, 70%)`;
  if (glyph === "↔") return `hsl(${Math.floor(pulse * 200)}, 100%, 60%)`;
  return `hsl(${Math.floor(pulse * 360)}, 80%, 75%)`;
}