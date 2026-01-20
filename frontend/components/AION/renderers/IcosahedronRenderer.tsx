"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html as DreiHtml } from "@react-three/drei";

interface IcosahedronRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    glyph?: string;
    logic_depth?: number;
    runtime_tick?: number;
  };
}

const IcosahedronRenderer: React.FC<IcosahedronRendererProps> = ({
  position,
  container,
}) => {
  // loosen all refs to any to avoid @types/three mismatch hell
  const shellRef = useRef<any>(null);
  const coreRef = useRef<any>(null);
  const latticeRef = useRef<any>(null);
  const glyphHaloRef = useRef<any>(null);

  /** 🔮 Glyph halo generator */
  useEffect(() => {
    if (!glyphHaloRef.current) return;
    glyphHaloRef.current.clear();

    const glyphTexture = createGlyphTexture(container.glyph || "⬡");
    const glyphMaterial = new THREE.SpriteMaterial({
      map: glyphTexture,
      transparent: true,
      opacity: 0.85,
    });

    const haloCount = 12;
    for (let i = 0; i < haloCount; i++) {
      const sprite = new THREE.Sprite(glyphMaterial.clone());
      sprite.scale.set(0.6, 0.6, 0.6);
      glyphHaloRef.current.add(sprite);
    }
  }, [container.glyph]);

  /** 🕸️ Geometric energy lattice inside */
  useEffect(() => {
    if (!latticeRef.current) return;
    latticeRef.current.clear();

    const lineMaterial = new THREE.LineBasicMaterial({
      color: "#00ffff",
      transparent: true,
      opacity: 0.5,
    });
    const geometry = new THREE.IcosahedronGeometry(2, 1);
    const edges = new THREE.EdgesGeometry(geometry);
    const line = new THREE.LineSegments(edges, lineMaterial);
    latticeRef.current.add(line);
  }, []);

  /** 🎛️ Animate rotations and shimmer */
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (shellRef.current) {
      shellRef.current.rotation.y += 0.002;
      const mat = shellRef.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 1 + Math.sin(t * 2) * 0.8;
    }

    if (coreRef.current) {
      coreRef.current.rotation.x -= 0.003;
      coreRef.current.rotation.y += 0.002;
      coreRef.current.scale.setScalar(1 + Math.sin(t * 1.5) * 0.2);
    }

    if (glyphHaloRef.current) {
      glyphHaloRef.current.children.forEach((glyph: any, i: number) => {
        const angle =
          t * 0.5 +
          (i * Math.PI * 2) / Math.max(glyphHaloRef.current!.children.length, 1);
        glyph.position.set(
          Math.cos(angle) * 3.2,
          Math.sin(angle * 1.2) * 1.5,
          Math.sin(angle) * 3.2
        );
      });
    }
  });

  return (
    <group position={position}>
      {/* 🏔 Outer Icosahedron Shell */}
      <mesh ref={shellRef}>
        <icosahedronGeometry args={[2.5, 0]} />
        <meshStandardMaterial
          color="#00eaff"
          emissive="#00ffff"
          emissiveIntensity={1.2}
          metalness={0.8}
          roughness={0.2}
          transparent
          opacity={0.5}
        />
      </mesh>

      {/* ✨ Inner Pulsing Core */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[0.8, 32, 32]} />
        <meshStandardMaterial
          color="#ffffff"
          emissive="#00f0ff"
          emissiveIntensity={2.5}
          transparent
          opacity={0.9}
        />
      </mesh>

      {/* 🔷 Energy Lattice */}
      <group ref={latticeRef} />

      {/* 🔮 Glyph Halo */}
      <group ref={glyphHaloRef} />

      {/* 🏷 Label */}
      <DreiHtml distanceFactor={14}>
        <div
          style={{
            textAlign: "center",
            fontSize: "0.8rem",
            color: "#00f8ff",
            textShadow: "0 0 10px #00f8ff",
          }}
        >
          ⬡ {container.name}
        </div>
      </DreiHtml>
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

export default IcosahedronRenderer;