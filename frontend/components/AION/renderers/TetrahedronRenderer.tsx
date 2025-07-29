"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";

interface TetrahedronRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    glyph?: string;
    runtime_tick?: number;
    logic_depth?: number;
  };
}

const TetrahedronRenderer: React.FC<TetrahedronRendererProps> = ({ position, container }) => {
  const tetraRef = useRef<THREE.Mesh>(null);
  const edgesRef = useRef<THREE.LineSegments>(null);
  const coreRef = useRef<THREE.Mesh>(null);
  const glyphOrbitRef = useRef<THREE.Group>(null);
  const auraRef = useRef<THREE.Mesh>(null);

  /** 🔮 Glyph Orbit Projectors */
  useEffect(() => {
    if (!glyphOrbitRef.current) return;
    glyphOrbitRef.current.clear();

    const glyphTexture = createGlyphTexture(container.glyph || "🔺");
    const glyphMaterial = new THREE.SpriteMaterial({
      map: glyphTexture,
      transparent: true,
      opacity: 0.9,
      depthWrite: false,
    });

    for (let i = 0; i < 4; i++) {
      const sprite = new THREE.Sprite(glyphMaterial.clone());
      sprite.scale.set(0.5, 0.5, 0.5);
      glyphOrbitRef.current.add(sprite);
    }
  }, [container.glyph]);

  /** 🎛 Animations */
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (tetraRef.current) {
      tetraRef.current.rotation.y = t * 0.6;
      tetraRef.current.rotation.x = Math.sin(t * 0.3) * 0.2;
    }

    if (edgesRef.current) {
      (edgesRef.current.material as THREE.LineBasicMaterial).opacity =
        0.6 + Math.sin(t * 2) * 0.3;
    }

    if (coreRef.current) {
      coreRef.current.scale.setScalar(0.8 + Math.sin(t * 3) * 0.2);
      (coreRef.current.material as THREE.MeshStandardMaterial).emissiveIntensity =
        1.5 + Math.sin(t * 4) * 0.8;
    }

    if (glyphOrbitRef.current) {
      glyphOrbitRef.current.children.forEach((glyph, i) => {
        const angle = t * 0.8 + i * (Math.PI / 2);
        glyph.position.set(Math.cos(angle) * 2.5, Math.sin(angle) * 2, Math.sin(angle) * 2.5);
      });
    }

    if (auraRef.current) {
      auraRef.current.scale.setScalar(1.3 + Math.sin(t * 1.5) * 0.1);
    }
  });

  return (
    <group position={position}>
      {/* 🔺 Main Tetrahedron */}
      <mesh ref={tetraRef}>
        <tetrahedronGeometry args={[2.5]} />
        <meshStandardMaterial
          color="#ff0077"
          emissive="#ff33aa"
          emissiveIntensity={0.8}
          metalness={0.6}
          roughness={0.3}
          transparent
          opacity={0.4}
        />
      </mesh>

      {/* ✨ Glowing Edges */}
      <lineSegments ref={edgesRef}>
        <edgesGeometry args={[new THREE.TetrahedronGeometry(2.5)]} />
        <lineBasicMaterial color="#ff33aa" linewidth={2} transparent opacity={0.8} />
      </lineSegments>

      {/* 🌟 Energy Core */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[0.6, 32, 32]} />
        <meshStandardMaterial
          color="#ffffff"
          emissive="#ff66cc"
          emissiveIntensity={2.2}
          transparent
          opacity={0.9}
        />
      </mesh>

      {/* 🔮 Glyph Orbit */}
      <group ref={glyphOrbitRef} />

      {/* 🌌 Aura Distortion */}
      <mesh ref={auraRef}>
        <sphereGeometry args={[3.5, 64, 64]} />
        <meshStandardMaterial
          color="#ff00aa"
          emissive="#ff33cc"
          emissiveIntensity={0.3}
          transparent
          opacity={0.2}
          side={THREE.BackSide}
        />
      </mesh>

      {/* 🏷 Label */}
      <Html distanceFactor={12}>
        <div style={{ textAlign: "center", fontSize: "0.8rem", color: "#ff33cc", textShadow: "0 0 12px #ff33cc" }}>
          🔺 {container.name}
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
  ctx.fillStyle = "#ff33cc";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(glyph, size / 2, size / 2);
  return new THREE.CanvasTexture(canvas);
}

export default TetrahedronRenderer;