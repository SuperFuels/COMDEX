'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { Canvas, useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';

interface ElectronData {
  meta: {
    label: string;
    linkContainerId: string;
  };
  glyphs: {
    type: string;
    value: string;
    confidence: number;
  }[];
}

interface AtomData {
  id: string;
  type: string;
  name: string;
  isAtom: boolean;
  position: [number, number, number];
  electronCount: number;
  electrons: ElectronData[];
}

export default function AtomElectronVisualizer() {
  const [atomData, setAtomData] = useState<AtomData | null>(null);

  useEffect(() => {
    fetch('/containers/atom_electrons_test.dc.json')
      .then((res) => res.json())
      .then((data) => setAtomData(data));
  }, []);

  if (!atomData) {
    return <div className="text-white p-4">⚛ Loading atom data...</div>;
  }

  // 🔍 Score and find the best-predicted electron
  const scored = atomData.electrons.map((e, i) => {
    const topGlyph = e.glyphs.reduce(
      (max, g) => (g.confidence > max.confidence ? g : max),
      e.glyphs[0]
    );
    return {
      index: i,
      confidence: topGlyph.confidence,
      glyph: topGlyph.value,
      label: e.meta.label
    };
  });
  const best = scored.reduce((max, e) => (e.confidence > max.confidence ? e : max), scored[0]);

  return (
    <div className="w-full h-[90vh] bg-black">
      <Canvas camera={{ position: [0, 0, 30], fov: 60 }}>
        <ambientLight />
        <pointLight position={[10, 10, 10]} />
        <Nucleus />
        {atomData.electrons.map((e, i) => (
          <Electron
            key={i}
            index={i}
            total={atomData.electrons.length}
            data={e}
            radius={10 + (i % 3) * 4}
            speed={0.01 + (i % 3) * 0.005}
            isBest={i === best.index}
          />
        ))}
      </Canvas>
    </div>
  );
}

function Nucleus() {
  return (
    <mesh>
      <sphereGeometry args={[2, 32, 32]} />
      <meshStandardMaterial color="#ff66cc" emissive="#aa00aa" />
    </mesh>
  );
}

function Electron({
  index,
  total,
  data,
  radius,
  speed,
  isBest,
}: {
  index: number;
  total: number;
  data: ElectronData;
  radius: number;
  speed: number;
  isBest: boolean;
}) {
  // loosen refs to `any` to dodge @types/three mismatch
  const ref = useRef<any>(null);
  const overlayRef = useRef<any>(null);
  const ringRef = useRef<any>(null);
  const angleRef = useRef(Math.random() * Math.PI * 2);
  const [hovered, setHovered] = useState(false);

  useFrame(() => {
    angleRef.current += speed;
    const a = angleRef.current + (index * 2 * Math.PI) / total;
    const x = Math.cos(a) * radius;
    const y = Math.sin(a) * radius;

    if (ref.current) {
      ref.current.position.set(x, y, 0);
    }

    if (overlayRef.current) {
      const s = 1 + 0.2 * Math.sin(Date.now() * 0.003);
      overlayRef.current.scale.set(s, s, s);
      overlayRef.current.position.set(x, y, 0);
    }

    if (ringRef.current) {
      ringRef.current.position.set(x, y, 0);
    }
  });

  const topGlyph = data.glyphs.reduce(
    (max, g) => (g.confidence > max.confidence ? g : max),
    data.glyphs[0]
  );
  const isGHX =
    topGlyph?.value.includes("GHX") ||
    topGlyph?.value.includes("⧖") ||
    topGlyph?.value.includes("⚛");

  const confidence = topGlyph?.confidence ?? 0;
  const color =
    confidence > 0.7 ? "#00ffcc" : confidence > 0.5 ? "#ffff66" : "#ff6666";

  const handleClick = async () => {
    const target = data.meta.linkContainerId;
    if (!target) return;

    try {
      const res = await fetch(`/api/teleport/${target}`);
      const json = await res.json();
      console.log("🛰️ Teleport result:", json);
      window.location.href = `/containers/${target}`;
    } catch (err) {
      console.error("⚠️ Teleport failed:", err);
    }
  };

  return (
    <group>
      <mesh
        ref={ref}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
        onClick={handleClick}
      >
        <sphereGeometry args={[isBest ? 1.0 : 0.7, 16, 16]} />
        <meshStandardMaterial color={color} emissive={color} />
        {hovered && (
          <Html center>
            <div className="bg-gray-900 border border-white text-white text-xs px-2 py-1 rounded shadow-md">
              <div className="font-bold">{data.meta.label}</div>
              {data.glyphs.map((g, i) => (
                <div key={i}>
                  {g.value}{" "}
                  <span className="text-green-300">
                    ({(g.confidence * 100).toFixed(1)}%)
                  </span>
                </div>
              ))}
              <div className="text-purple-400 mt-1">Click → teleport</div>
            </div>
          </Html>
        )}
      </mesh>

      {isBest && (
        <mesh ref={ringRef}>
          <ringGeometry args={[1.1, 1.4, 32]} />
          <meshBasicMaterial color="gold" side={THREE.DoubleSide} />
        </mesh>
      )}

      {isGHX && (
        <mesh ref={overlayRef}>
          <sphereGeometry args={[1.2, 16, 16]} />
          <meshStandardMaterial
            emissive="cyan"
            emissiveIntensity={1.5}
            transparent
            opacity={0.4}
          />
        </mesh>
      )}
    </group>
  );
}