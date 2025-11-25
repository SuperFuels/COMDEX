"use client";

import React, { useRef, useMemo } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { TextGeometry } from "three/examples/jsm/geometries/TextGeometry";
import { FontLoader, Font } from "three/examples/jsm/loaders/FontLoader";
import helvetiker from "three/examples/fonts/helvetiker_regular.typeface.json";

interface WormholeRendererProps {
  from: [number, number, number];
  to: [number, number, number];
  color?: string;
  thickness?: number;
  glyph?: string;
  mode?: "solid" | "dashed" | "glow";
  pulse?: boolean;
  pulseFlow?: boolean;
}

export default function WormholeRenderer({
  from,
  to,
  color = "#ff00ff",
  thickness = 0.02,
  glyph,
  mode = "glow",
  pulse = false,
  pulseFlow = false,
}: WormholeRendererProps) {
  const lineRef = useRef<any>(null);
  const textRef = useRef<any>(null);

  const points = useMemo(
    () => [new THREE.Vector3(...from), new THREE.Vector3(...to)],
    [from, to]
  );

  const geometry = useMemo(
    () => new THREE.BufferGeometry().setFromPoints(points),
    [points]
  );

  const material = useMemo(() => {
    const mat = new THREE.LineBasicMaterial({
      color,
      linewidth: thickness,
      transparent: true,
      opacity: mode === "glow" ? 0.7 : 1,
    });
    if (mode === "glow") {
      mat.depthWrite = false;
      mat.blending = THREE.AdditiveBlending;
    }
    return mat;
  }, [color, thickness, mode]);

  const font = useMemo(() => {
    const loader = new FontLoader();
    return loader.parse(helvetiker as any) as Font;
  }, []);

  const textGeometry = useMemo(() => {
    if (!glyph) return null;
    return new TextGeometry(glyph, { font, size: 0.3, depth: 0.05 });
  }, [glyph, font]);

  useFrame(({ clock }) => {
    if (pulse && lineRef.current && lineRef.current.material) {
      const mat = lineRef.current.material as THREE.Material;
      const intensity = 0.5 + 0.5 * Math.sin(clock.elapsedTime * 4);
      mat.opacity = intensity;
      mat.needsUpdate = true;
    }
  });

  const mid = useMemo(
    () => new THREE.Vector3().addVectors(points[0], points[1]).multiplyScalar(0.5),
    [points]
  );
  const midArray = useMemo(
    () => mid.toArray() as [number, number, number],
    [mid]
  );

  return (
    <>
      {/* line */}
      <primitive object={new THREE.Line(geometry, material)} ref={lineRef as any} />

      {/* glyph at midpoint */}
      {glyph && textGeometry && (
        <mesh ref={textRef as any} position={midArray}>
          <primitive object={textGeometry as any} attach="geometry" />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={1.5}
          />
        </mesh>
      )}
    </>
  );
}