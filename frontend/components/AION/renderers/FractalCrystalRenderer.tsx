"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";

interface FractalCrystalRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    glyph?: string;
    logic_depth?: number;
    runtime_tick?: number;
  };
}

const FractalCrystalRenderer: React.FC<FractalCrystalRendererProps> = ({ position, container }) => {
  const outerRef = useRef<THREE.Mesh>(null);
  const innerRef = useRef<THREE.Mesh>(null);
  const shardsRef = useRef<THREE.Group>(null);
  const glyphGroupRef = useRef<THREE.Group>(null);

  /** 🎨 Glyph holograms orbiting the crystal */
  useEffect(() => {
    if (!glyphGroupRef.current) return;
    glyphGroupRef.current.clear();
    const glyphTexture = createGlyphTexture(container.glyph || "✧");
    const glyphMaterial = new THREE.SpriteMaterial({ map: glyphTexture, transparent: true, opacity: 0.85 });

    for (let i = 0; i < 8; i++) {
      const sprite = new THREE.Sprite(glyphMaterial.clone());
      sprite.scale.set(0.5, 0.5, 0.5);
      glyphGroupRef.current.add(sprite);
    }
  }, [container.glyph]);

  /** 🌌 Procedural crystal shards generation */
  useEffect(() => {
    if (!shardsRef.current) return;
    shardsRef.current.clear();

    const shardMaterial = new THREE.MeshStandardMaterial({
      color: "#00ffff",
      emissive: "#00e0ff",
      emissiveIntensity: 1,
      metalness: 0.7,
      roughness: 0.1,
      transparent: true,
      opacity: 0.5,
    });

    for (let i = 0; i < 12; i++) {
      const shard = new THREE.Mesh(new THREE.TetrahedronGeometry(0.5), shardMaterial.clone());
      const angle = (i / 12) * Math.PI * 2;
      shard.position.set(Math.cos(angle) * 2, Math.sin(i * 0.5) * 1.5, Math.sin(angle) * 2);
      shard.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI);
      shardsRef.current.add(shard);
    }
  }, []);

  /** 🌀 Animate fractal spin, shards, spectral glow, and glyphs */
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (outerRef.current) {
      outerRef.current.rotation.y += 0.003;
      (outerRef.current.material as THREE.MeshStandardMaterial).emissiveIntensity =
        1.5 + Math.sin(t * 3) * 0.8;
    }
    if (innerRef.current) {
      innerRef.current.rotation.x -= 0.004;
      innerRef.current.scale.setScalar(1 + Math.sin(t * 2.5) * 0.2);
    }
    if (shardsRef.current) {
      shardsRef.current.children.forEach((shard, i) => {
        shard.rotation.y += 0.01 * ((i % 2) ? 1 : -1);
      });
    }
    if (glyphGroupRef.current) {
      glyphGroupRef.current.children.forEach((glyph, i) => {
        const angle = t * 0.7 + i * (Math.PI / 4);
        glyph.position.set(Math.cos(angle) * 3, Math.sin(t * 0.4 + i) * 2, Math.sin(angle) * 3);
      });
    }
  });

  return (
    <group position={position}>
      {/* 🧊 Outer Crystal */}
      <mesh ref={outerRef}>
        <octahedronGeometry args={[2, 1]} />
        <meshStandardMaterial
          color="#a0f0ff"
          emissive="#00f0ff"
          emissiveIntensity={1.2}
          metalness={0.8}
          roughness={0.2}
          transparent
          opacity={0.6}
        />
      </mesh>

      {/* 💎 Inner Rotating Core */}
      <mesh ref={innerRef}>
        <dodecahedronGeometry args={[0.8, 0]} />
        <meshStandardMaterial
          color="#ffffff"
          emissive="#80f0ff"
          emissiveIntensity={2.5}
          transparent
          opacity={0.85}
        />
      </mesh>

      {/* 🔹 Fractal Crystal Shards */}
      <group ref={shardsRef} />

      {/* 🔮 Orbiting Glyph Holograms */}
      <group ref={glyphGroupRef} />

      {/* 🏷 Label */}
      <Html distanceFactor={14}>
        <div style={{ textAlign: "center", fontSize: "0.8rem", color: "#00f8ff", textShadow: "0 0 10px #00f8ff" }}>
          ✧ {container.name}
        </div>
      </Html>
    </group>
  );
};

/** 🖌️ Glyph Texture Generator */
function createGlyphTexture(glyph: string): THREE.Texture {
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  ctx.clearRect(0, 0, size, size);
  ctx.font = "bold 90px sans-serif";
  ctx.fillStyle = "#00ffff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(glyph, size / 2, size / 2);
  return new THREE.CanvasTexture(canvas);
}

export default FractalCrystalRenderer;