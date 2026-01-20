"use client";

import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { Html as DreiHtml } from "@react-three/drei";

interface MemoryHaloProps {
  glyphs: { symbol: string; weight?: number }[]; // glyph + memory density
  radius?: number;
  rotationSpeed?: number;
  avatarRef: React.RefObject<THREE.Object3D>;
}

export default function MemoryHaloRing({
  glyphs,
  radius = 1.8,
  rotationSpeed = 0.002,
  avatarRef,
}: MemoryHaloProps) {
  // 👇 loosen type to dodge @types/three vs three mismatch
  const ringRef = useRef<any>(null);
  const [positions, setPositions] = useState<THREE.Vector3[]>([]);
  const pulseRef = useRef<number>(0);

  useEffect(() => {
    const angleStep = (2 * Math.PI) / Math.max(glyphs.length, 1);
    const newPositions = glyphs.map((_, i) => {
      const angle = i * angleStep;
      const x = radius * Math.cos(angle);
      const z = radius * Math.sin(angle);
      const y = 0.1 * Math.sin(angle * 2); // small vertical wobble
      return new THREE.Vector3(x, y, z);
    });
    setPositions(newPositions);
  }, [glyphs, radius]);

  useFrame((_, delta) => {
    if (ringRef.current && avatarRef.current) {
      ringRef.current.rotation.y += rotationSpeed;
      ringRef.current.position.copy(avatarRef.current.position);
    }
    pulseRef.current += delta * 2.5;
  });

  return (
    <group
      // 👇 use callback ref instead of passing RefObject directly
      ref={(el: any) => {
        ringRef.current = el;
      }}
    >
      {glyphs.map((g, i) => {
        const pos = positions[i] || new THREE.Vector3();
        const intensity = Math.min(Math.max(g.weight ?? 0.5, 0.2), 1.2); // Clamp 0.2–1.2
        const color = getMemoryColor(g.symbol);
        const opacity = 0.7 + 0.3 * Math.sin(pulseRef.current + i);

        return (
          <DreiHtml key={i} position={[pos.x, pos.y, pos.z]} center distanceFactor={16}>
            <div
              style={{
                color,
                fontSize: `${7 * intensity}px`,
                lineHeight: 1,
                fontWeight: 600,
                textShadow: "0 0 6px rgba(0,0,0,0.6)",
                opacity,
                userSelect: "none",
              }}
            >
              {g.symbol}
            </div>
          </DreiHtml>
        );
      })}
    </group>
  );
}

function getMemoryColor(symbol: string): string {
  switch (symbol) {
    case "↔":
      return "#aa00ff";
    case "⬁":
      return "#00ffff";
    case "⧖":
      return "#ffaa00";
    case "🧠":
      return "#ffffff";
    default:
      return "#bbbbbb";
  }
}