// frontend/components/QuantumField/EmotionPulseOverlay.tsx
"use client";

import React, { useEffect, useState } from "react";
import { Html as DreiHtml } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import type { GlyphNode } from "@/types/qfc";

// 🎯 Emotion → color
const EMOTION_COLORS: Record<string, string> = {
  frustration: "#f87171", // red
  curiosity: "#38bdf8",   // blue
  insight: "#34d399",     // green
};

// --- helpers ---------------------------------------------------------------

type EmotionNormalized = { type: string; intensity: number };

/** Accepts string, object, null/undefined; returns normalized object or null */
function normalizeEmotion(e: unknown): EmotionNormalized | null {
  if (!e) return null;
  if (typeof e === "string") {
    return { type: e, intensity: 0.8 };
  }
  if (typeof e === "object" && "type" in (e as any)) {
    const obj = e as { type?: unknown; intensity?: unknown };
    const type = typeof obj.type === "string" ? obj.type : "";
    if (!type) return null;
    const intensity =
      typeof obj.intensity === "number" ? obj.intensity : 0.8;
    return { type, intensity };
  }
  return null;
}

/** Accept array or {x,y,z}; always return [x,y,z] */
function toXYZ(p: unknown): [number, number, number] {
  if (Array.isArray(p) && p.length >= 3) {
    const [x, y, z] = p as number[];
    return [Number(x) || 0, Number(y) || 0, Number(z) || 0];
  }
  if (p && typeof p === "object") {
    const anyP = p as any;
    return [
      Number(anyP.x) || 0,
      Number(anyP.y) || 0,
      Number(anyP.z) || 0,
    ];
  }
  return [0, 0, 0];
}

function colorFor(type: string): string {
  return EMOTION_COLORS[type] ?? "#aaaaaa";
}

// ----------------------------
// ✅ 1) HTML overlay pulse
// ----------------------------
export const HtmlEmotionPulse: React.FC<{ node: GlyphNode }> = ({ node }) => {
  const emo = normalizeEmotion((node as any).emotion);
  if (!emo) return null;

  const pos = toXYZ((node as any).position);
  const color = colorFor(emo.type);
  const sizeRem = Math.min(1.5, 0.5 + Math.max(0, emo.intensity));

  return (
    <DreiHtml position={pos} zIndexRange={[1, 0]} center>
      <div
        className="animate-ping absolute rounded-full opacity-75"
        style={{
          width: `${sizeRem}rem`,
          height: `${sizeRem}rem`,
          backgroundColor: color,
        }}
      />
    </DreiHtml>
  );
};

// ----------------------------
// ✅ 2) 3D mesh pulse
// ----------------------------
export const MeshEmotionPulse: React.FC<{ node: GlyphNode }> = ({ node }) => {
  const [pulse, setPulse] = useState(0);

  useFrame((_, delta) => {
    setPulse((prev) => (prev + delta * 2) % (Math.PI * 2));
  });

  const emo = normalizeEmotion((node as any).emotion);
  if (!emo) return null;

  const pos = toXYZ((node as any).position);
  const color = colorFor(emo.type);
  const scale = 1 + 0.2 * Math.sin(pulse);

  return (
    <mesh position={pos} scale={[scale, scale, scale]}>
      <sphereGeometry args={[0.12, 16, 16]} />
      <meshBasicMaterial color={color} transparent opacity={0.6} depthWrite={false} />
    </mesh>
  );
};