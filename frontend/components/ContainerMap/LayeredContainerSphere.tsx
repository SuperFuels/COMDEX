"use client";

import * as THREE from "three";
import React, { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";

type GlyphLayer = {
  symbol: string;
  layer: number; // 0 = inner, 1 = mid, 2 = outer
};

type Props = {
  glyphs: GlyphLayer[];
  radius?: number;
  rotationSpeed?: number;
};

export default function LayeredContainerSphere({
  glyphs,
  radius = 1.0,
  rotationSpeed = 0.002,
}: Props) {
  const groupRef = useRef<THREE.Group>(null);
  const timeRef = useRef(0);

  const layerColors = ["#ffffff", "#7cf7ff", "#b181ff"];
  const radiusOffsets = [0.6, 0.9, 1.3];

  const grouped = useMemo(() => {
    const layerMap: Record<number, GlyphLayer[]> = { 0: [], 1: [], 2: [] };
    for (const g of glyphs) {
      if (layerMap[g.layer]) layerMap[g.layer].push(g);
    }
    return layerMap;
  }, [glyphs]);

  useFrame((_, delta) => {
    timeRef.current += delta;
    if (groupRef.current) {
      groupRef.current.rotation.y += rotationSpeed;
    }
  });

  return (
    <group ref={groupRef}>
      {[0, 1, 2].map((layer) => {
        const glyphsInLayer = grouped[layer];
        const angleStep = (2 * Math.PI) / Math.max(glyphsInLayer.length, 1);
        const offset = radiusOffsets[layer] * radius;

        return glyphsInLayer.map((glyph, i) => {
          const angle = i * angleStep;
          const pulse = 0.5 + 0.5 * Math.sin(timeRef.current * (1 + layer * 0.3) + i);
          const x = Math.cos(angle) * offset;
          const y = 0.15 * layer * Math.sin(angle * 2);
          const z = Math.sin(angle) * offset;

          return (
            <Text
              key={`${layer}-${i}-${glyph.symbol}`}
              position={[x, y, z]}
              fontSize={0.08 + 0.02 * pulse}
              color={getSymbolColor(glyph.symbol) || layerColors[layer]}
              anchorX="center"
              anchorY="middle"
              outlineWidth={0.002}
              outlineColor="black"
            >
              {glyph.symbol}
            </Text>
          );
        });
      })}
    </group>
  );
}

function getSymbolColor(symbol: string): string | undefined {
  switch (symbol) {
    case "⊕": return "#ffcc00";
    case "↔": return "#aa00ff";
    case "⧖": return "#00ffff";
    case "🧠": return "#00ff66";
    case "⬁": return "#ff6666";
    case "→": return "#66ccff";
    default: return undefined;
  }
}