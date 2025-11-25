"use client";

import * as THREE from "three";
import React, { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";

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
  // loosen ref type to avoid @types/three version mismatch
  const groupRef = useRef<any>(null);
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
      (groupRef.current as THREE.Group).rotation.y += rotationSpeed;
    }
  });

  return (
    <group ref={groupRef as any}>
      {[0, 1, 2].map((layer) => {
        const glyphsInLayer = grouped[layer];
        const angleStep = (2 * Math.PI) / Math.max(glyphsInLayer.length, 1);
        const offset = radiusOffsets[layer] * radius;

        return glyphsInLayer.map((glyph, i) => {
          const angle = i * angleStep;
          const pulse =
            0.5 + 0.5 * Math.sin(timeRef.current * (1 + layer * 0.3) + i);
          const x = Math.cos(angle) * offset;
          const y = 0.15 * layer * Math.sin(angle * 2);
          const z = Math.sin(angle) * offset;
          const color = getSymbolColor(glyph.symbol) || layerColors[layer];

          return (
            <mesh key={`${layer}-${i}-${glyph.symbol}`} position={[x, y, z]}>
              {/* little glowing node */}
              <sphereGeometry args={[0.06 + 0.02 * pulse, 12, 12]} />
              <meshStandardMaterial
                color={color}
                emissive={color}
                emissiveIntensity={0.8}
              />
              {/* crisp label via Html (avoids drei <Text/> typings) */}
              <Html distanceFactor={12}>
                <div
                  style={{
                    fontSize: "10px",
                    color,
                    textShadow: "0 0 6px rgba(0,0,0,0.6)",
                    userSelect: "none",
                    lineHeight: 1,
                  }}
                >
                  {glyph.symbol}
                </div>
              </Html>
            </mesh>
          );
        });
      })}
    </group>
  );
}

function getSymbolColor(symbol: string): string | undefined {
  switch (symbol) {
    case "⊕":
      return "#ffcc00";
    case "↔":
      return "#aa00ff";
    case "⧖":
      return "#00ffff";
    case "🧠":
      return "#00ff66";
    case "⬁":
      return "#ff6666";
    case "→":
      return "#66ccff";
    default:
      return undefined;
  }
}