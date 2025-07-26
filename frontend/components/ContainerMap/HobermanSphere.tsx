import React, { useRef, useEffect, useState } from "react";
import { animated, useSpring } from "@react-spring/three";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";

interface HobermanSphereProps {
  position: [number, number, number];
  containerId: string;
  active?: boolean;
  glyph?: string;
  logicDepth?: number;
  runtimeTick?: number;
  soulLocked?: boolean;
}

export default function HobermanSphere({
  position,
  containerId,
  active = false,
  glyph,
  logicDepth = 0,
  runtimeTick = 0,
  soulLocked = false,
}: HobermanSphereProps) {
  const groupRef = useRef<THREE.Group>(null);
  const [tickState, setTickState] = useState(runtimeTick);

  const targetScale =
    soulLocked || logicDepth === 0 ? 0.001 : 0.5 + logicDepth * 0.15;

  const scaleSpring = useSpring({
    scale: targetScale,
    config: { mass: 2, tension: 200, friction: 25 },
  });

  const animatedScale = scaleSpring.scale.to((s) => [s, s, s]);

  useFrame(() => {
    if (groupRef.current && active) {
      groupRef.current.rotation.y += 0.01;
    }
  });

  useEffect(() => {
    if (runtimeTick !== tickState) {
      setTickState(runtimeTick);
    }
  }, [runtimeTick]);

  const glowColor =
    glyph === "↔"
      ? "#9933ff"
      : glyph === "⧖"
      ? "#00e0ff"
      : glyph === "🧬"
      ? "#66ff99"
      : "#888";

  return (
    <animated.group
      ref={groupRef}
      position={position}
      scale={animatedScale as unknown as [number, number, number]}
    >
      {/* Core Mesh */}
      <mesh>
        <sphereGeometry args={[1, 32, 32]} />
        <meshStandardMaterial
          color={glowColor}
          emissive={glowColor}
          emissiveIntensity={1.5}
          transparent
          opacity={0.08}
        />
      </mesh>

      {/* Glow Ring for ↔ entanglement */}
      {glyph === "↔" && (
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[1.2, 1.4, 64]} />
          <meshBasicMaterial
            color="#cc66ff"
            transparent
            opacity={0.5}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}

      {/* Trail Pulse */}
      {(glyph === "↔" || glyph === "⧖" || glyph === "🧬") && (
        <mesh>
          <sphereGeometry args={[1.6, 32, 32]} />
          <meshStandardMaterial
            color={glowColor}
            emissive={glowColor}
            emissiveIntensity={0.7}
            transparent
            opacity={0.06}
          />
        </mesh>
      )}

      {/* Label tag */}
      <Html distanceFactor={12}>
        <div
          style={{
            fontSize: "0.6rem",
            color: "#ccc",
            textAlign: "center",
            marginTop: "4px",
            background: "#0008",
            padding: "2px 6px",
            borderRadius: 6,
          }}
        >
          {containerId}
        </div>
      </Html>
    </animated.group>
  );
}