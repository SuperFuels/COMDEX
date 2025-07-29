"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";

interface TorusRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    glyph?: string;
    runtime_tick?: number;
    logic_depth?: number;
  };
}

const TorusRenderer: React.FC<TorusRendererProps> = ({ position, container }) => {
  const torusRef = useRef<THREE.Mesh>(null);
  const plasmaRef = useRef<THREE.Mesh>(null);
  const glyphOrbitRef = useRef<THREE.Group>(null);
  const exhaustJetsRef = useRef<THREE.Group>(null);

  /** 🔮 Glyph Orbit Projectors */
  useEffect(() => {
    if (!glyphOrbitRef.current) return;
    glyphOrbitRef.current.clear();

    const glyphTexture = createGlyphTexture(container.glyph || "⭕");
    const glyphMaterial = new THREE.SpriteMaterial({
      map: glyphTexture,
      transparent: true,
      opacity: 0.9,
      depthWrite: false,
    });

    for (let i = 0; i < 6; i++) {
      const sprite = new THREE.Sprite(glyphMaterial.clone());
      sprite.scale.set(0.5, 0.5, 0.5);
      glyphOrbitRef.current.add(sprite);
    }
  }, [container.glyph]);

  /** 🔥 Exhaust Jets Setup */
  useEffect(() => {
    if (!exhaustJetsRef.current) return;
    exhaustJetsRef.current.clear();

    for (let i = 0; i < 4; i++) {
      const jet = new THREE.Mesh(
        new THREE.ConeGeometry(0.2, 1.2, 16),
        new THREE.MeshStandardMaterial({
          color: "#ff8800",
          emissive: "#ff5500",
          emissiveIntensity: 2,
          transparent: true,
          opacity: 0.7,
        })
      );
      jet.rotation.x = Math.PI;
      jet.position.set(Math.cos((i * Math.PI) / 2) * 2.5, 0, Math.sin((i * Math.PI) / 2) * 2.5);
      exhaustJetsRef.current.add(jet);
    }
  }, []);

  /** 🎛 Animations */
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (torusRef.current) {
      torusRef.current.rotation.x = t * 0.6;
      torusRef.current.rotation.y = t * 0.4;
    }

    if (plasmaRef.current) {
      plasmaRef.current.rotation.z = -t * 0.8;
      (plasmaRef.current.material as THREE.MeshStandardMaterial).opacity =
        0.3 + Math.sin(t * 4) * 0.1;
    }

    if (glyphOrbitRef.current) {
      glyphOrbitRef.current.children.forEach((glyph, i) => {
        const angle = t * 0.7 + i * (Math.PI / 3);
        glyph.position.set(Math.cos(angle) * 3, Math.sin(angle) * 1.5, Math.sin(angle) * 3);
        (glyph as THREE.Sprite).material.opacity = 0.6 + Math.sin(t * 3 + i) * 0.3;
      });
    }

    if (exhaustJetsRef.current) {
      exhaustJetsRef.current.children.forEach((jet, i) => {
        jet.scale.y = 1 + 0.3 * Math.sin(t * 5 + i);
      });
    }
  });

  return (
    <group position={position}>
      {/* 🔵 Main Torus */}
      <mesh ref={torusRef}>
        <torusGeometry args={[2.5, 0.3, 32, 128]} />
        <meshStandardMaterial
          color="#00aaff"
          emissive="#00ccff"
          emissiveIntensity={1.5}
          metalness={0.7}
          roughness={0.2}
        />
      </mesh>

      {/* 🌌 Inner Plasma Ring */}
      <mesh ref={plasmaRef} scale={[1.2, 1.2, 1.2]}>
        <torusGeometry args={[2, 0.15, 16, 64]} />
        <meshStandardMaterial
          color="#00ffff"
          emissive="#00ffff"
          emissiveIntensity={2}
          transparent
          opacity={0.4}
        />
      </mesh>

      {/* 🔥 Exhaust Jets */}
      <group ref={exhaustJetsRef} />

      {/* 🔮 Glyph Orbit */}
      <group ref={glyphOrbitRef} />

      {/* 🏷 Label */}
      <Html distanceFactor={12}>
        <div style={{ textAlign: "center", fontSize: "0.8rem", color: "#00ffff", textShadow: "0 0 12px #00f0ff" }}>
          ⭕ {container.name}
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

export default TorusRenderer;