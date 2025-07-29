"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";

interface OctahedronRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    glyph?: string;
    runtime_tick?: number;
    logic_depth?: number;
  };
}

const OctahedronRenderer: React.FC<OctahedronRendererProps> = ({ position, container }) => {
  const coreRef = useRef<THREE.Mesh>(null);
  const edgesRef = useRef<THREE.LineSegments>(null);
  const glyphOrbitRef = useRef<THREE.Group>(null);

  /** 🔶 Setup glowing octahedron edges */
  useEffect(() => {
    if (!edgesRef.current) return;

    const geo = new THREE.EdgesGeometry(new THREE.OctahedronGeometry(1, 0));
    const mat = new THREE.LineBasicMaterial({ color: "#00eaff", linewidth: 2 });
    edgesRef.current.geometry = geo;
    edgesRef.current.material = mat;
  }, []);

  /** 🔮 Glyph Orbits (floating holograms) */
  useEffect(() => {
    if (!glyphOrbitRef.current) return;
    glyphOrbitRef.current.clear();

    const glyphTexture = createGlyphTexture(container.glyph || "🔷");
    const glyphMaterial = new THREE.SpriteMaterial({
      map: glyphTexture,
      transparent: true,
      opacity: 0.8,
      depthWrite: false,
    });

    for (let i = 0; i < 6; i++) {
      const sprite = new THREE.Sprite(glyphMaterial.clone());
      sprite.scale.set(0.5, 0.5, 0.5);
      glyphOrbitRef.current.add(sprite);
    }
  }, [container.glyph]);

  /** 🎛 Animate core, edges, and glyphs */
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (coreRef.current) {
      coreRef.current.rotation.x += 0.005;
      coreRef.current.rotation.y += 0.006;
      (coreRef.current.material as THREE.MeshStandardMaterial).emissiveIntensity =
        1 + Math.sin(t * 4) * 0.4;
    }

    if (edgesRef.current) {
      edgesRef.current.rotation.y += 0.004;
      edgesRef.current.rotation.z += 0.002;
    }

    if (glyphOrbitRef.current) {
      glyphOrbitRef.current.children.forEach((glyph, i) => {
        const angle = t * 0.8 + i * (Math.PI / 3);
        glyph.position.set(Math.cos(angle) * 2, Math.sin(angle * 1.2) * 1, Math.sin(angle) * 2);
        (glyph as THREE.Sprite).material.opacity = 0.5 + Math.sin(t * 2 + i) * 0.3;
      });
    }
  });

  return (
    <group position={position}>
      {/* 🔷 Core Octahedron */}
      <mesh ref={coreRef}>
        <octahedronGeometry args={[1, 0]} />
        <meshStandardMaterial
          color="#00eaff"
          emissive="#00ffff"
          emissiveIntensity={1.2}
          metalness={0.8}
          roughness={0.2}
          transparent
          opacity={0.95}
        />
      </mesh>

      {/* 🔶 Edges Glow */}
      <lineSegments ref={edgesRef} />

      {/* 🔮 Glyph Orbits */}
      <group ref={glyphOrbitRef} />

      {/* 🏷 Label */}
      <Html distanceFactor={12}>
        <div style={{ textAlign: "center", fontSize: "0.8rem", color: "#00eaff", textShadow: "0 0 10px #00ffff" }}>
          🔶 {container.name}
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
  ctx.fillStyle = "#00eaff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(glyph, size / 2, size / 2);
  return new THREE.CanvasTexture(canvas);
}

export default OctahedronRenderer;