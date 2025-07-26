import React, { useRef, useMemo, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { MeshDistortMaterial, Sphere, Html, Text, Ring } from "@react-three/drei";
import { animated, useSpring } from "@react-spring/three";
import * as THREE from "three";

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

function ExpansionCore({
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
  const meshRef = useRef<THREE.Mesh>(null);
  const logicDepth = expandedLogic?.logic_tree?.depth || 1;
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
      meshRef.current.rotation.y += 0.003;
    }
  });

  return (
    <group>
      <animated.mesh
        ref={meshRef}
        scale={scale.to((s: number) => [s, s, s])}
        onClick={() => setClicked(true)}
      >
        <sphereGeometry args={[1, 64, 64]} />
        <MeshDistortMaterial
          color={isEntangled ? "#b377f1" : isInMemory ? "#00ffaa" : "#00ccff"}
          distort={isCollapsed ? 0.1 : 0.4}
          speed={isCollapsed ? 0.25 : 1.2}
          emissive={
            isEntangled
              ? new THREE.Color("#b377f1")
              : isInMemory
              ? new THREE.Color("#00ffaa")
              : new THREE.Color("#00ccff")
          }
          emissiveIntensity={isEntangled ? 1.5 : isInMemory ? 1.2 : 0.6}
          transparent
          opacity={0.92}
        />
      </animated.mesh>

      {isInMemory && (
        <Ring args={[1.1, 1.25, 64]}>
          <meshBasicMaterial color="#00ffaa" opacity={0.5} transparent />
        </Ring>
      )}

      {glyphOverlay.map((glyph: string, i: number) => (
        <Text
          key={i}
          position={[Math.cos(i) * 1.2, Math.sin(i) * 1.2, 0]}
          fontSize={0.15}
          color="#ffffff"
        >
          {glyph}
        </Text>
      ))}

      <Html center position={[0, -1.5, 0]}>
        <div style={{ fontSize: "0.85rem", color: "#ccc", fontFamily: "monospace" }}>
          {containerId}
        </div>
      </Html>
    </group>
  );
}
export default ExpansionCore;