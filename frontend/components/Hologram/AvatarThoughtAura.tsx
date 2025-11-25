"use client";

import React, { useRef, useMemo, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { MeshDistortMaterial, Html } from "@react-three/drei";
import { animated, useSpring } from "@react-spring/three";

interface SymbolicExpansionSphereProps {
  containerId: string;
  expandedLogic?: any;
  runtimeTick?: number;
  glyphOverlay?: string[];
  isEntangled?: boolean;
  isCollapsed?: boolean;
  isInMemory?: boolean;
  isActive?: boolean;
  mode?: "pulse" | "depth" | "logic";
}

// drei typing quirk with our r3f version: give the material a loose alias
const Distort = MeshDistortMaterial as unknown as React.ComponentType<any>;

export default function ExpansionCore({
  expandedLogic,
  runtimeTick = 0,
  isEntangled = false,
  isCollapsed = false,
  isInMemory = false,
  isActive = false,
  mode = "depth",
  containerId,
  glyphOverlay = [],
}: SymbolicExpansionSphereProps) {
  // loosen ref type to dodge @types/three mismatch
  const meshRef = useRef<any>(null);

  const logicDepth = expandedLogic?.logic_tree?.depth ?? 1;
  const [clicked, setClicked] = useState(false);

  const baseScale = useMemo(() => {
    if (isCollapsed) return 0.5;
    if (mode === "pulse") return Math.sin(runtimeTick * 0.1) * 0.1 + 1;
    if (mode === "depth") return Math.min(logicDepth / 10, 2.5) + 1;
    return 1;
  }, [logicDepth, runtimeTick, isCollapsed, mode]);

  const { scale } = useSpring({
    scale: clicked ? baseScale * 1.25 : baseScale,
    config: { tension: 120, friction: 14 },
    onRest: () => setClicked(false),
  });

  useFrame(() => {
    if (meshRef.current) {
      (meshRef.current as THREE.Mesh).rotation.y += 0.003;
    }
  });

  const emissive = isEntangled ? "#b377f1" : isInMemory ? "#00ffaa" : "#00ccff";

  return (
    <group>
      <animated.mesh
        ref={meshRef as any}
        scale={scale.to((s: number) => [s, s, s]) as any}
        onClick={() => setClicked(true)}
      >
        <sphereGeometry args={[1, 64, 64]} />
        <Distort
          attach="material"
          color={emissive}
          distort={isCollapsed ? 0.1 : 0.4}
          speed={isCollapsed ? 0.25 : 1.2}
          emissive={emissive}
          emissiveIntensity={isEntangled ? 1.5 : isInMemory ? 1.2 : 0.6}
          transparent
          opacity={0.92}
        />
      </animated.mesh>

      {/* Memory halo ring */}
      {isInMemory && (
        <mesh>
          <ringGeometry args={[1.1, 1.25, 64]} />
          <meshBasicMaterial color="#00ffaa" opacity={0.5} transparent />
        </mesh>
      )}

      {/* Glyph overlay labels */}
      {glyphOverlay.map((glyph, i) => {
        const x = Math.cos(i) * 1.2;
        const y = Math.sin(i) * 1.2;
        return (
          <Html key={i} position={[x, y, 0]} distanceFactor={12}>
            <div
              style={{
                fontSize: "12px",
                color: "#ffffff",
                textShadow: "0 0 6px rgba(0,0,0,0.6)",
                userSelect: "none",
                lineHeight: 1,
              }}
            >
              {glyph}
            </div>
          </Html>
        );
      })}

      {/* Container label */}
      <Html center position={[0, -1.5, 0]}>
        <div
          style={{
            fontSize: "0.85rem",
            color: "#ccc",
            fontFamily: "monospace",
          }}
        >
          {containerId}
        </div>
      </Html>
    </group>
  );
}