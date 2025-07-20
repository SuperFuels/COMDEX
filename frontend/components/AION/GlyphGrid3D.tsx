import React, { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";

export interface GlyphGrid3DProps {
  cubes: { [coord: string]: { glyph?: string; age_ms?: number; denied?: boolean } };
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

const GlyphCube = ({ x, y, z, coord, data, onClick }: any) => {
  const color = getColor(data.glyph, data.age_ms, data.denied);
  const label = data.glyph || "";

  return (
    <mesh
      position={[x, z, y]}
      onClick={() => onClick?.(coord, data)}
      castShadow
      receiveShadow
    >
      <boxGeometry args={[0.9, 0.9, 0.9]} />
      <meshStandardMaterial color={color} />
      {label && (
        <Html center distanceFactor={10} style={{ fontSize: "10px", pointerEvents: "none" }}>
          {label}
        </Html>
      )}
    </mesh>
  );
};

const GlyphGrid3D: React.FC<GlyphGrid3DProps> = ({ cubes, onGlyphClick }) => {
  const glyphCubes = useMemo(() => {
    return Object.entries(cubes).map(([coord, data]) => {
      const [x, y, z] = coord.split(",").map(Number);
      return <GlyphCube key={coord} x={x} y={y} z={z} coord={coord} data={data} onClick={onGlyphClick} />;
    });
  }, [cubes, onGlyphClick]);

  return (
    <div style={{ width: "100%", height: "600px" }}>
      <Canvas shadows camera={{ position: [10, 10, 10], fov: 50 }}>
        <ambientLight intensity={0.6} />
        <pointLight position={[10, 20, 10]} intensity={1} castShadow />
        <OrbitControls enableDamping />
        {glyphCubes}
      </Canvas>
    </div>
  );
};

export default GlyphGrid3D;