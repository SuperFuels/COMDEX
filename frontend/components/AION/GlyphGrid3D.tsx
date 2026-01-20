'use client';

import React, { useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Html as DreiHtml } from "@react-three/drei";
import * as THREE from "three";

export interface GlyphGrid3DProps {
  cubes: {
    [coord: string]: {
      glyph?: string;
      age_ms?: number;
      denied?: boolean;
    };
  };
  onGlyphClick?: (coord: string, data: any) => void;
}

const getColor = (glyph: string, age_ms?: number, denied?: boolean) => {
  if (denied) return "#f87171"; // red
  if (!glyph) return "#f9fafb"; // white
  if (glyph === "⚙") return "#fef08a"; // yellow
  if (glyph === "🧠") return "#e9d5ff"; // purple
  if (glyph === "🔒") return "#fecaca"; // pink
  if (glyph === "🌐") return "#bae6fd"; // blue
  if (age_ms && age_ms > 60000) return "#d1d5db"; // gray
  return "#e5e7eb"; // default gray
};

const GlyphCube = ({
  x,
  y,
  z,
  coord,
  data,
  onClick,
}: {
  x: number;
  y: number;
  z: number;
  coord: string;
  data: { glyph?: string; age_ms?: number; denied?: boolean };
  onClick?: (coord: string, data: any) => void;
}) => {
  const [hovered, setHovered] = useState(false);
  const color = getColor(data.glyph || "", data.age_ms, data.denied);
  const label = data.glyph || "";
  const scale = hovered ? 1.1 : 1.0;

  return (
    <mesh
      position={[x, z, y]}
      scale={[scale, scale, scale]}
      onClick={() => onClick?.(coord, data)}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
      castShadow
      receiveShadow
    >
      <boxGeometry args={[0.9, 0.9, 0.9]} />
      <meshStandardMaterial color={color} emissive={data.denied ? "#f87171" : "#000000"} emissiveIntensity={data.denied ? 0.5 : 0} />
      {label && (
        <DreiHtml center distanceFactor={8} style={{ fontSize: "10px", pointerEvents: "none" }}>
          {label}
        </DreiHtml>
      )}
    </mesh>
  );
};

const GlyphGrid3D: React.FC<GlyphGrid3DProps> = ({ cubes, onGlyphClick }) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const glyphCubes = useMemo(() => {
    return Object.entries(cubes).map(([coord, data]) => {
      const [x, y, z] = coord.split(",").map(Number);
      return (
        <GlyphCube
          key={coord}
          x={x}
          y={y}
          z={z}
          coord={coord}
          data={data}
          onClick={onGlyphClick}
        />
      );
    });
  }, [cubes, onGlyphClick]);

  if (!mounted) return null;

  return (
    <div style={{ width: "100%", height: "600px", minHeight: "600px", overflow: "visible" }}>
      <Canvas shadows camera={{ position: [10, 10, 10], fov: 50 }}>
        <ambientLight intensity={0.6} />
        <pointLight position={[10, 20, 10]} intensity={1.2} castShadow />
        <OrbitControls enableDamping />
        {glyphCubes}
      </Canvas>
    </div>
  );
};

export default GlyphGrid3D;