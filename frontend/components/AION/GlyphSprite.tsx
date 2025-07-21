// File: frontend/components/AION/GlyphSprite.tsx

import React, { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";

interface GlyphSpriteProps {
  position: [number, number, number];
  glyph: string;
  scale?: number;
  float?: boolean;
  color?: string;
}

export default function GlyphSprite({
  position,
  glyph,
  scale = 0.4,
  float = true,
  color = "#ffffff",
}: GlyphSpriteProps) {
  const ref = useRef<any>();

  useFrame(({ clock }) => {
    if (float && ref.current) {
      const t = clock.getElapsedTime();
      ref.current.position.y = position[1] + Math.sin(t * 2) * 0.2;
      ref.current.rotation.y = t * 0.5;
    }
  });

  return (
    <Text
      ref={ref}
      position={position}
      fontSize={scale}
      color={color}
      outlineColor="black"
      outlineWidth={0.03}
      anchorX="center"
      anchorY="middle"
    >
      {glyph}
    </Text>
  );
}