import React, { useEffect, useState } from "react";
import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { GlyphNode } from "@types/qfc";

// ----------------------------
// 🎯 Emotion Color Mapping
// ----------------------------
const emotionColors: Record<string, string> = {
  frustration: "#f87171", // red
  curiosity: "#38bdf8",   // blue
  insight: "#34d399",     // green
};

// ----------------------------
// ✅ 1. HTML Overlay Version
// ----------------------------
export const HtmlEmotionPulse: React.FC<{ node: GlyphNode }> = ({ node }) => {
  if (!node.emotion) return null;

  const { type, intensity } = node.emotion;
  const color = emotionColors[type] || "#aaa";
  const size = Math.min(1.5, 0.5 + intensity);

  return (
    <Html position={node.position} zIndexRange={[1, 0]} center>
      <div
        className="animate-ping absolute rounded-full opacity-75"
        style={{
          width: `${size}rem`,
          height: `${size}rem`,
          backgroundColor: color,
        }}
      />
    </Html>
  );
};

// ----------------------------
// ✅ 2. 3D Mesh Version
// ----------------------------
export const MeshEmotionPulse: React.FC<{ node: GlyphNode }> = ({ node }) => {
  const [pulse, setPulse] = useState(0);

  useFrame((_, delta) => {
    setPulse((prev) => (prev + delta * 2) % (2 * Math.PI));
  });

  if (!node.emotion) return null;

  const { type } = node.emotion;
  const color = emotionColors[type] || "#aaa";
  const scale = 1 + 0.2 * Math.sin(pulse);

  return (
    <mesh position={node.position} scale={[scale, scale, scale]}>
      <sphereGeometry args={[0.12, 16, 16]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.6}
        depthWrite={false}
      />
    </mesh>
  );
};