import React, { useEffect, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import * as THREE from "three";

interface ThoughtAuraProps {
  glyphs: string[]; // List of active glyphs (symbolic)
  radius?: number;
  avatarRef: React.RefObject<THREE.Object3D>; // Reference to the avatar's 3D model
}

const rotationSpeed = 0.005;
const pulseSpeed = 3.0;

export default function AvatarThoughtAura({ glyphs, radius = 1.2, avatarRef }: ThoughtAuraProps) {
  const [positions, setPositions] = useState<THREE.Vector3[]>([]);
  const auraGroup = useRef<THREE.Group>(null);
  const pulseRef = useRef<number>(0);

  useEffect(() => {
    const angleStep = (2 * Math.PI) / glyphs.length;
    const newPositions = glyphs.map((_, i) => {
      const angle = i * angleStep;
      const x = radius * Math.cos(angle);
      const z = radius * Math.sin(angle);
      return new THREE.Vector3(x, 0.3, z);
    });
    setPositions(newPositions);
  }, [glyphs, radius]);

  useFrame((_, delta) => {
    if (auraGroup.current && avatarRef.current) {
      auraGroup.current.rotation.y += rotationSpeed;
      auraGroup.current.position.copy(avatarRef.current.position);
    }
    pulseRef.current += delta * pulseSpeed;
  });

  return (
    <group ref={auraGroup}>
      {glyphs.map((glyph, i) => {
        const baseColor = isCollapseGlyph(glyph) ? getPulseColor(pulseRef.current) : "white";
        const opacity = 0.9 + 0.1 * Math.sin(pulseRef.current + i);
        return (
          <Text
            key={i}
            position={positions[i] || new THREE.Vector3()}
            fontSize={0.08}
            color={baseColor}
            anchorX="center"
            anchorY="middle"
            outlineWidth={0.003}
            outlineColor="#000000"
            fillOpacity={opacity}
          >
            {glyph}
          </Text>
        );
      })}
    </group>
  );
}

function isCollapseGlyph(glyph: string): boolean {
  return glyph === "⧖" || glyph === "⬁" || glyph === "↔";
}

function getPulseColor(t: number): string {
  const hue = (t * 40) % 360;
  return `hsl(${hue}, 100%, 70%)`;
}