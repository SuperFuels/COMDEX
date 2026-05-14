"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html as DreiHtml } from "@react-three/drei";

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

const TesseractRenderer: React.FC<TesseractRendererProps> = ({
  position,
  container,
}) => {
  // loosen ref types to avoid @types/three version conflicts
  const outerCubeRef = useRef<any>(null);
  const innerCubeRef = useRef<any>(null);
  const edgesRef = useRef<any>(null);
  const glyphOrbitRef = useRef<any>(null);
  const distortionFieldRef = useRef<any>(null);

  /** 🔮 Glyph Orbit Projectors */
  useEffect(() => {
    if (!glyphOrbitRef.current) return;
    const group = glyphOrbitRef.current as THREE.Group;
    group.clear();

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
      group.add(sprite);
    }
  }, [container.glyph]);

  /** ✨ Edge Lines geometry/material setup */
  useEffect(() => {
    if (!edgesRef.current) return;
    const lines = edgesRef.current as THREE.LineSegments;

    const geo = new THREE.EdgesGeometry(new THREE.BoxGeometry(3.5, 3.5, 3.5));
    const mat = new THREE.LineBasicMaterial({
      color: "#00ffff",
      linewidth: 2,
    });

    lines.geometry = geo;
    lines.material = mat;

    return () => {
      geo.dispose();
      mat.dispose();
    };
  }, []);

  /** 🎛 Animate cubes and glyphs */
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (outerCubeRef.current) {
      const mesh = outerCubeRef.current as THREE.Mesh;
      mesh.rotation.x = Math.sin(t * 0.6) * 0.5;
      mesh.rotation.y = Math.cos(t * 0.8) * 0.5;
    }

    if (innerCubeRef.current) {
      const mesh = innerCubeRef.current as THREE.Mesh;
      mesh.rotation.x = Math.cos(t * 0.7) * 1.2;
      mesh.rotation.y = Math.sin(t * 0.9) * 1.2;
    }

    if (edgesRef.current) {
      const lines = edgesRef.current as THREE.LineSegments;
      lines.rotation.y += 0.003;
    }

    if (distortionFieldRef.current) {
      const mesh = distortionFieldRef.current as THREE.Mesh;
      mesh.scale.setScalar(1 + 0.15 * Math.sin(t * 2));
      const mat = mesh.material as THREE.MeshStandardMaterial;
      mat.opacity = 0.25 + 0.1 * Math.sin(t * 2.5);
    }

    if (glyphOrbitRef.current) {
      const group = glyphOrbitRef.current as THREE.Group;
      group.children.forEach((glyph: any, i: number) => {
        const angle = t * 0.6 + (i * Math.PI) / 4;
        glyph.position.set(
          Math.cos(angle) * 2.5,
          Math.sin(angle * 1.4) * 1.5,
          Math.sin(angle) * 2.5
        );
        if (glyph.material instanceof THREE.SpriteMaterial) {
          glyph.material.opacity = 0.5 + Math.sin(t * 3 + i) * 0.4;
        }
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
      <lineSegments ref={edgesRef} />

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
      <DreiHtml distanceFactor={12}>
        <div
          style={{
            textAlign: "center",
            fontSize: "0.8rem",
            color: "#00ffff",
            textShadow: "0 0 12px #00f0ff",
          }}
        >
          ⧈ {container.name}
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

export default TesseractRenderer;