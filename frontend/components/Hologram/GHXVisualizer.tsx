import { useEffect, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";

// Example glyph data
const exampleGlyphs = [
  { id: "g1", glyph: "⊕", position: [0, 0, 0], color: "white" },
  { id: "g2", glyph: "↔", position: [2, 0, 0], color: "violet" },
  { id: "g3", glyph: "🧠", position: [0, 2, 0], color: "cyan" },
  { id: "g4", glyph: "⧖", position: [-2, 0, 0], color: "gold" },
];

const GlyphHologram = ({ glyph, position, color }: any) => {
  const meshRef = useRef<any>();
  useFrame(() => {
    if (meshRef.current) meshRef.current.rotation.y += 0.01;
  });
  return (
    <mesh ref={meshRef} position={position}>
      <sphereGeometry args={[0.4, 32, 32]} />
      <meshStandardMaterial emissive={color} emissiveIntensity={1.5} color="black" />
      <Html center>
        <div style={{ color: color, fontSize: "1.2em", fontWeight: "bold" }}>{glyph}</div>
      </Html>
    </mesh>
  );
};

const LightLinks = ({ glyphs }: any) => {
  const lines = [];
  glyphs.forEach((g: any) => {
    if (g.entangled) {
      g.entangled.forEach((targetId: string) => {
        const target = glyphs.find((x: any) => x.id === targetId);
        if (target) {
          lines.push(
            <line key={`${g.id}-${target.id}`}>
              <bufferGeometry>
                <bufferAttribute
                  attach="attributes-position"
                  count={2}
                  array={new Float32Array([...g.position, ...target.position])}
                  itemSize={3}
                />
              </bufferGeometry>
              <lineBasicMaterial color="white" linewidth={2} />
            </line>
          );
        }
      });
    }
  });
  return <>{lines}</>;
};

const GHXVisualizer = ({ glyphs = exampleGlyphs }: any) => {
  return (
    <Canvas style={{ height: "100vh", background: "black" }} camera={{ position: [0, 0, 8] }}>
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={1.2} />
      {glyphs.map((g: any) => (
        <GlyphHologram key={g.id} {...g} />
      ))}
      <LightLinks glyphs={glyphs} />
      <OrbitControls />
    </Canvas>
  );
};

export default GHXVisualizer;