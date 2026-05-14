// File: GHXSignatureTrail.tsx

"use client";

import React, { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html as DreiHtml } from "@react-three/drei";

interface TrailOverlayMetadata {
  label: string;
  concept_match_score?: number;
  semantic_distance?: number;
  intensity?: number; // optional glow intensity for trail
}

// Helper: convert soulHash or identity into color hue
function soulHashToHue(soulHash: string): number {
  let hash = 0;
  for (let i = 0; i < soulHash.length; i++) {
    hash = soulHash.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash % 360);
}

export default function GHXSignatureTrail({
  identity = "GHXNode.identity",
  radius = 2.2,
  speed = 1,
  overlayMetadata = [],
}: {
  identity?: string;
  radius?: number;
  speed?: number;
  overlayMetadata?: TrailOverlayMetadata[];
}) {
  const trailRef = useRef<any>(null);

  const hue = soulHashToHue(identity);
  // use plain CSS color string instead of THREE.Color to dodge type mismatch
  const baseColor = useMemo(
    () => `hsl(${hue}, 80%, 60%)`,
    [hue]
  );

  // Compute glow from overlay intensity (fallback to 1.0)
  const emissiveIntensity = useMemo(() => {
    const max = overlayMetadata?.[0]?.intensity ?? 1;
    return Math.min(2.5, Math.max(0.5, max)); // Clamp
  }, [overlayMetadata]);

  useFrame(({ clock }) => {
    if (trailRef.current) {
      const t = clock.getElapsedTime();
      const x = radius * Math.cos(t * speed);
      const z = radius * Math.sin(t * speed);
      (trailRef.current as THREE.Mesh).position.set(x, 0, z);
      (trailRef.current as THREE.Mesh).rotation.y = t * speed;
    }
  });

  return (
    <mesh ref={trailRef}>
      <torusGeometry args={[0.2, 0.05, 16, 100]} />
      <meshStandardMaterial
        color={baseColor}
        emissive={baseColor}
        emissiveIntensity={emissiveIntensity}
      />
      <DreiHtml center>
        <div
          style={{
            color: baseColor,
            fontSize: "0.9em",
            fontWeight: "bold",
            opacity: 0.9,
            textShadow: "0 0 4px rgba(255,255,255,0.5)",
          }}
        >
          🧬
        </div>
      </DreiHtml>
    </mesh>
  );
}