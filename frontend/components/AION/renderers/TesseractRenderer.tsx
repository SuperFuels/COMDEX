"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";

interface TesseractRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    glyph?: string;
    runtime_tick?: number;
    logic_depth?: number;
  };
}

const TesseractRenderer: React.FC<TesseractRendererProps> = ({ position, container }) => {
  const outerCubeRef = useRef<THREE.Mesh>(null);
  const innerCubeRef = useRef<THREE.Mesh>(null);
  const edgesRef = useRef<THREE.LineSegments>(null);
  const glyphOrbitRef = useRef<THREE.Group>(null);
  const distortionFieldRef = useRef<THREE.Mesh>(null);

  /** 🔮 Glyph Orbit Projectors */
  useEffect(() => {
    if (!glyphOrbitRef.current) return;
    glyphOrbitRef.current.clear();

    const glyphTexture = createGlyphTexture(container.glyph || "⧈");
    const glyphMaterial = new THREE.SpriteMaterial({
      map: glyphTexture,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
    });

    for (let i = 0; i < 8; i++) {
      const sprite = new THREE.Sprite(glyphMaterial.clone());
      sprite.scale.set(0.5, 0.5, 0.5);
      glyphOrbitRef.current.add(sprite);
    }
  }, [container.glyph]);

  /** 🎛 Animate cubes and glyphs */
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (outerCubeRef.current) {
      outerCubeRef.current.rotation.x = Math.sin(t * 0.6) * 0.5;
      outerCubeRef.current.rotation.y = Math.cos(t * 0.8) * 0.5;
    }

    if (innerCubeRef.current) {
      innerCubeRef.current.rotation.x = Math.cos(t * 0.7) * 1.2;
      innerCubeRef.current.rotation.y = Math.sin(t * 0.9) * 1.2;
    }

    if (edgesRef.current) {
      edgesRef.current.rotation.y += 0.003;
    }

    if (distortionFieldRef.current) {
      distortionFieldRef.current.scale.setScalar(1 + 0.15 * Math.sin(t * 2));
      (distortionFieldRef.current.material as THREE.MeshStandardMaterial).opacity =
        0.25 + 0.1 * Math.sin(t * 2.5);
    }

    if (glyphOrbitRef.current) {
      glyphOrbitRef.current.children.forEach((glyph, i) => {
        const angle = t * 0.6 + i * (Math.PI / 4);
        glyph.position.set(Math.cos(angle) * 2.5, Math.sin(angle * 1.4) * 1.5, Math.sin(angle) * 2.5);
        (glyph as THREE.Sprite).material.opacity = 0.5 + Math.sin(t * 3 + i) * 0.4;
      });
    }
  });

  return (
    <group position={position}>
      {/* 🟦 Outer Hypercube */}
      <mesh ref={outerCubeRef}>
        <boxGeometry args={[2.5, 2.5, 2.5]} />
        <meshStandardMaterial
          color="#00ffff"
          emissive="#00f0ff"
          emissiveIntensity={1.2}
          metalness={0.8}
          roughness={0.2}
          transparent
          opacity={0.4}
        />
      </mesh>

      {/* 🟩 Inner Hypercube */}
      <mesh ref={innerCubeRef} scale={[0.7, 0.7, 0.7]}>
        <boxGeometry args={[2.5, 2.5, 2.5]} />
        <meshStandardMaterial
          color="#00ffff"
          emissive="#00f0ff"
          emissiveIntensity={1.5}
          metalness={0.6}
          roughness={0.1}
          transparent
          opacity={0.5}
        />
      </mesh>

      {/* ✨ Edge Lines */}
      <lineSegments ref={edgesRef}>
        <edgesGeometry args={[new THREE.BoxGeometry(3.5, 3.5, 3.5)]} />
        <lineBasicMaterial color="#00ffff" linewidth={2} />
      </lineSegments>

      {/* 🌌 Distortion Field */}
      <mesh ref={distortionFieldRef}>
        <sphereGeometry args={[4.5, 64, 64]} />
        <meshStandardMaterial
          color="#00ffff"
          emissive="#00ffff"
          emissiveIntensity={0.3}
          transparent
          opacity={0.2}
          side={THREE.BackSide}
        />
      </mesh>

      {/* 🔮 Glyph Orbits */}
      <group ref={glyphOrbitRef} />

      {/* 🏷 Label */}
      <Html distanceFactor={12}>
        <div style={{ textAlign: "center", fontSize: "0.8rem", color: "#00ffff", textShadow: "0 0 12px #00f0ff" }}>
          ⧈ {container.name}
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

export default TesseractRenderer;