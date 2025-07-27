import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Html, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import GHXSignatureTrail from './GHXSignatureTrail';
import { useEffect, useState } from 'react';
import axios from 'axios';

const useGHXGlyphs = () => {
  const [holograms, setHolograms] = useState<any[]>([]);
  const [echoes, setEchoes] = useState<any[]>([]);

  useEffect(() => {
    axios.get("/api/replay/list?include_metadata=true&sort_by_time=true").then(res => {
      const allGlyphs = res.data.result || [];

      const holograms = [];
      const echoes = [];

      for (const g of allGlyphs) {
        const isEcho = g.metadata?.memoryEcho || g.metadata?.source === "memory";
        const glyphObj = {
          id: g.id,
          glyph: g.content,
          position: [Math.random() * 6 - 3, Math.random() * 4 - 2, Math.random() * 4 - 2],
          color: isEcho ? "#555577" : "#ffffff",
          memoryEcho: isEcho,
          entangled: g.metadata?.entangled_ids || [],
        };

        if (isEcho) echoes.push(glyphObj);
        else holograms.push(glyphObj);
      }

      setHolograms(holograms);
      setEchoes(echoes);
    });
  }, []);

  return { holograms, echoes };
};

const GlyphHologram = ({ glyph, position, color, memoryEcho }: any) => {
  const meshRef = useRef<any>();
  const isMutation = glyph === "⬁";

  useFrame(({ clock }) => {
    if (meshRef.current && isMutation) {
      const t = clock.getElapsedTime();
      const pulse = 1 + 0.3 * Math.sin(t * 4);
      meshRef.current.material.emissiveIntensity = pulse;
      meshRef.current.scale.set(pulse, pulse, pulse);
    }
  });

  return (
    <mesh ref={meshRef} position={position}>
      <sphereGeometry args={[0.4, 32, 32]} />
      <meshStandardMaterial
        emissive={memoryEcho ? "#222222" : color}
        emissiveIntensity={memoryEcho ? 0.3 : 1.5}
        transparent={memoryEcho}
        opacity={memoryEcho ? 0.35 : 1}
        color={memoryEcho ? "#111111" : isMutation ? "#220000" : "black"}
      />
      <Html center>
        <div style={{
          color: memoryEcho ? "#666" : color,
          fontSize: memoryEcho ? "0.9em" : "1.2em",
          opacity: memoryEcho ? 0.6 : 1,
          textAlign: "center"
        }}>
          {glyph}
          {isMutation && <div style={{ fontSize: "0.8em", color: "#ff6666" }}>⬁</div>}
        </div>
      </Html>
    </mesh>
  );
};

const LightLinks = ({ glyphs }: any) => {
  const lines = [];

  glyphs.forEach((g: any) => {
    if (g.entangled) {
      g.entangled.forEach((targetId: string) => {
        const target = glyphs.find((other: any) => other.id === targetId);
        if (target) {
          lines.push([g.position, target.position]);
        }
      });
    }
  });

  return (
    <>
      {lines.map((line, idx) => (
        <line key={idx}>
          <bufferGeometry attach="geometry">
            <bufferAttribute
              attach="attributes-position"
              count={2}
              array={new Float32Array([...line[0], ...line[1]])}
              itemSize={3}
            />
          </bufferGeometry>
          <lineBasicMaterial color="violet" linewidth={2} />
        </line>
      ))}
    </>
  );
};

const QEntropySpiral = () => {
  const meshRef = useRef<any>();

  useFrame(({ clock }) => {
    if (meshRef.current) {
      const t = clock.getElapsedTime();
      const angle = t * 1.5;
      const radius = 1.5 + 0.2 * Math.sin(t * 2);
      const x = radius * Math.cos(angle);
      const y = 0.5 * Math.sin(angle * 2);
      const z = radius * Math.sin(angle);

      meshRef.current.position.set(x, y, z);
      meshRef.current.rotation.y = angle;
      meshRef.current.scale.setScalar(1 + 0.2 * Math.sin(t * 4));
    }
  });

  return (
    <mesh ref={meshRef}>
      <torusGeometry args={[0.25, 0.1, 16, 100]} />
      <meshStandardMaterial color="#88ccff" emissive="#2299ff" emissiveIntensity={1.2} />
      <Html center>
        <div style={{
          color: "#88ccff",
          fontSize: "1.1em",
          textShadow: "0 0 6px #2299ff",
        }}>
          🌀
        </div>
      </Html>
    </mesh>
  );
};

export default function GHXVisualizer() {
  const { holograms, echoes } = useGHXGlyphs();

  return (
    <Canvas camera={{ position: [0, 0, 10], fov: 60 }}>
      <ambientLight intensity={0.4} />
      <pointLight position={[10, 10, 10]} intensity={1} />

      {/* Memory Echo Glyphs */}
      {echoes.map((g) => (
        <GlyphHologram
          key={`echo-${g.id}`}
          glyph={g.glyph}
          position={g.position}
          color={g.color}
          memoryEcho={true}
        />
      ))}

      {/* Active Holograms */}
      {holograms.map((g) => (
        <GlyphHologram
          key={g.id}
          glyph={g.glyph}
          position={g.position}
          color={g.color}
          memoryEcho={false}
        />
      ))}

      <LightLinks glyphs={[...holograms]} />
      <QEntropySpiral />
      <GHXSignatureTrail identity={"AION-000X"} radius={2.2} />
      <OrbitControls />
    </Canvas>
  );
}