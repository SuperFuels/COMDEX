// File: frontend/components/AION/WormholeRenderer.tsx
import React, { useRef } from "react";
import { Vector3, Quaternion } from "three";
import { useFrame } from "@react-three/fiber";
import { Line2 } from "three/examples/jsm/lines/Line2";
import { LineMaterial } from "three/examples/jsm/lines/LineMaterial";
import { LineGeometry } from "three/examples/jsm/lines/LineGeometry";
import { createGlowMaterial } from "./WormholeEffectMaterial";
import GlyphSprite from "./GlyphSprite";

interface WormholeProps {
  from: [number, number, number];
  to: [number, number, number];
  color?: string;
  thickness?: number;
  pulse?: boolean;
  arrow?: boolean;
  mode?: "solid" | "dashed" | "glow";
  glyph?: string;
  pulseFlow?: boolean;
}

export default function WormholeRenderer({
  from,
  to,
  color = "#66f",
  thickness = 0.03,
  pulse = true,
  arrow = true,
  mode = "solid",
  glyph,
  pulseFlow = false,
}: WormholeProps) {
  const cylinderRef = useRef<any>(null);
  const coneRef = useRef<any>(null);
  const particleRef = useRef<any>(null);

  const start = new Vector3(...from);
  const end = new Vector3(...to);
  const direction = new Vector3().subVectors(end, start);
  const mid = new Vector3().addVectors(start, end).multiplyScalar(0.5);
  const length = direction.length();

  const up = new Vector3(0, 1, 0);
  const quaternion = new Quaternion().setFromUnitVectors(
    up,
    direction.clone().normalize()
  );

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    if (pulse && cylinderRef.current) {
      const scale = 1 + Math.sin(t * 3) * 0.3;
      cylinderRef.current.scale.set(scale, 1, scale);
    }

    if (pulse && coneRef.current) {
      const scale = 1 + Math.sin(t * 3) * 0.2;
      coneRef.current.scale.set(scale, scale, scale);
    }

    if (pulseFlow && particleRef.current) {
      const progress = (t * 0.5) % 1;
      const pos = new Vector3().lerpVectors(start, end, progress);
      particleRef.current.position.set(pos.x, pos.y, pos.z);
    }
  });

  const renderWormholeBody = () => {
    if (mode === "dashed") {
      const points = [start.toArray(), end.toArray()];
      const geometry = new LineGeometry();
      geometry.setPositions(points.flat());

      const material = new LineMaterial({
        color,
        linewidth: thickness * 10,
        dashed: true,
        dashSize: 0.3,
        gapSize: 0.2,
        transparent: true,
        opacity: 0.6,
      });

      return (
        <primitive
          object={new Line2(geometry, material)}
          position={[0, 0, 0]}
          quaternion={quaternion}
        />
      );
    }

    return (
      <mesh position={mid} quaternion={quaternion} ref={cylinderRef}>
        <cylinderGeometry args={[thickness, thickness, length, 16]} />
        {mode === "glow" ? (
          <primitive object={createGlowMaterial(color)} attach="material" />
        ) : (
          <meshStandardMaterial
            color="black"
            emissive={color}
            emissiveIntensity={1.8}
            transparent
            opacity={0.6}
          />
        )}
      </mesh>
    );
  };

  return (
    <>
      {renderWormholeBody()}

      {/* Optional animated flow particle */}
      {pulseFlow && (
        <mesh ref={particleRef}>
          <sphereGeometry args={[thickness * 1.2, 8, 8]} />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={2.2}
          />
        </mesh>
      )}

      {/* Optional arrowhead */}
      {arrow && (
        <mesh position={end} quaternion={quaternion} ref={coneRef}>
          <coneGeometry args={[thickness * 2, thickness * 4, 8]} />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={1.2}
          />
        </mesh>
      )}

      {/* Optional floating glyph */}
      {glyph && <GlyphSprite position={mid.toArray()} glyph={glyph} />}
    </>
  );
}