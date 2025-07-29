"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";

interface DodecahedronRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    glyph?: string;
    runtime_tick?: number;
    logic_depth?: number;
  };
}

const DodecahedronRenderer: React.FC<DodecahedronRendererProps> = ({ position, container }) => {
  const dodeRef = useRef<THREE.Mesh>(null);
  const edgesRef = useRef<THREE.LineSegments>(null);
  const latticeRef = useRef<THREE.Group>(null);
  const glyphOrbitRef = useRef<THREE.Group>(null);
  const glowRef = useRef<THREE.Mesh>(null);

  /** 🔮 Glyph Orbit Projectors */
  useEffect(() => {
    if (!glyphOrbitRef.current) return;
    glyphOrbitRef.current.clear();

    const glyphTexture = createGlyphTexture(container.glyph || "⬟");
    const glyphMaterial = new THREE.SpriteMaterial({
      map: glyphTexture,
      transparent: true,
      opacity: 0.9,
      depthWrite: false,
    });

    for (let i = 0; i < 6; i++) {
      const sprite = new THREE.Sprite(glyphMaterial.clone());
      sprite.scale.set(0.6, 0.6, 0.6);
      glyphOrbitRef.current.add(sprite);
    }
  }, [container.glyph]);

  /** 🌐 Internal Lattice Generator */
  useEffect(() => {
    if (!latticeRef.current) return;
    latticeRef.current.clear();

    const latticeMat = new THREE.MeshStandardMaterial({
      color: "#55ffff",
      emissive: "#00ffff",
      emissiveIntensity: 1.5,
      transparent: true,
      opacity: 0.3,
    });

    for (let i = 0; i < 8; i++) {
      const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.3, 16, 16), latticeMat);
      sphere.position.set(
        (Math.random() - 0.5) * 3,
        (Math.random() - 0.5) * 3,
        (Math.random() - 0.5) * 3
      );
      latticeRef.current.add(sphere);
    }
  }, []);

  /** 🎛 Animations */
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (dodeRef.current) {
      dodeRef.current.rotation.y = t * 0.4;
      dodeRef.current.rotation.x = Math.sin(t * 0.3) * 0.2;
    }

    if (edgesRef.current) {
      (edgesRef.current.material as THREE.LineBasicMaterial).opacity =
        0.6 + Math.sin(t * 2) * 0.3;
    }

    if (latticeRef.current) {
      latticeRef.current.rotation.y = -t * 0.6;
    }

    if (glyphOrbitRef.current) {
      glyphOrbitRef.current.children.forEach((glyph, i) => {
        const angle = t * 0.6 + i * ((2 * Math.PI) / 6);
        glyph.position.set(Math.cos(angle) * 3, Math.sin(angle * 1.5), Math.sin(angle) * 3);
      });
    }

    if (glowRef.current) {
      glowRef.current.scale.setScalar(3.8 + Math.sin(t * 1.8) * 0.1);
    }
  });

  return (
    <group position={position}>
      {/* ⬟ Main Dodecahedron */}
      <mesh ref={dodeRef}>
        <dodecahedronGeometry args={[2.5]} />
        <meshStandardMaterial
          color="#00ffff"
          emissive="#33ffff"
          emissiveIntensity={0.8}
          metalness={0.4}
          roughness={0.2}
          transparent
          opacity={0.35}
        />
      </mesh>

      {/* ✨ Glowing Edges */}
      <lineSegments ref={edgesRef}>
        <edgesGeometry args={[new THREE.DodecahedronGeometry(2.5)]} />
        <lineBasicMaterial color="#33ffff" linewidth={2} transparent opacity={0.8} />
      </lineSegments>

      {/* 🔷 Internal Energy Lattice */}
      <group ref={latticeRef} />

      {/* 🔮 Glyph Orbit */}
      <group ref={glyphOrbitRef} />

      {/* 🌌 Outer Glow Aura */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[4.5, 64, 64]} />
        <meshStandardMaterial
          color="#00ffff"
          emissive="#33ffff"
          emissiveIntensity={0.3}
          transparent
          opacity={0.15}
          side={THREE.BackSide}
        />
      </mesh>

      {/* 🏷 Label */}
      <Html distanceFactor={12}>
        <div style={{ textAlign: "center", fontSize: "0.8rem", color: "#33ffff", textShadow: "0 0 12px #33ffff" }}>
          ⬟ {container.name}
        </div>
      </Html>
    </group>
  );
};

/** 🖌 Glyph Texture Generator */
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

export default DodecahedronRenderer;