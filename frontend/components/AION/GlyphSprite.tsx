// File: frontend/components/AION/GlyphSprite.tsx
"use client";

import React, { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html as DreiHtml } from "@react-three/drei";
import * as THREE from "three";

interface GlyphSpriteProps {
  position: [number, number, number];
  glyph: string;
  scale?: number; // visual scale multiplier
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
  // 👇 loosen type so it doesn't conflict with the other three typings
  const groupRef = useRef<any>(null);

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    if (float) {
      const t = clock.getElapsedTime();
      groupRef.current.position.set(
        position[0],
        position[1] + Math.sin(t * 2) * 0.2,
        position[2]
      );
      groupRef.current.rotation.y = t * 0.5;
    } else {
      groupRef.current.position.set(position[0], position[1], position[2]);
    }
  });

  return (
    <group ref={groupRef} position={position}>
      <DreiHtml center transform>
        <div
          style={{
            color,
            fontSize: `${Math.max(10, Math.round(scale * 48))}px`,
            fontWeight: 700,
            textShadow: "0 0 6px rgba(0,0,0,0.6)",
            userSelect: "none",
            pointerEvents: "none",
            lineHeight: 1,
          }}
        >
          {glyph}
        </div>
      </DreiHtml>
    </group>
  );
}