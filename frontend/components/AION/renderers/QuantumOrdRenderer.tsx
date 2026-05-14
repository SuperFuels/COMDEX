"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html as DreiHtml } from "@react-three/drei";

interface QuantumOrdRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    glyph?: string;
    runtime_tick?: number;
    logic_depth?: number;
  };
}

const QuantumOrdRenderer: React.FC<QuantumOrdRendererProps> = ({
  position,
  container,
}) => {
  // 🔧 loosen ref typing to dodge @types/three version mismatches
  const coreRef = useRef<any>(null);
  const latticeRef = useRef<any>(null);
  const glyphOrbitRef = useRef<any>(null);
  const pulseFieldRef = useRef<any>(null);

  /** 🌌 Quantum Lattice (Point Cloud) */
  useEffect(() => {
    if (!latticeRef.current) return;

    const geometry = new THREE.BufferGeometry();
    const points: number[] = [];

    for (let i = 0; i < 500; i++) {
      const r = 1.8;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const x = r * Math.sin(phi) * Math.cos(theta);
      const y = r * Math.sin(phi) * Math.sin(theta);
      const z = r * Math.cos(phi);
      points.push(x, y, z);
    }

    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(points, 3)
    );

    const material = new THREE.PointsMaterial({
      color: "#ff00ff",
      size: 0.05,
      transparent: true,
      opacity: 0.8,
    });

    const pointsObj = latticeRef.current as THREE.Points;
    pointsObj.geometry = geometry;
    pointsObj.material = material;
  }, []);

  /** 🔮 Glyph Orbit Projectors */
  useEffect(() => {
    if (!glyphOrbitRef.current) return;
    glyphOrbitRef.current.clear();

    const glyphTexture = createGlyphTexture(container.glyph || "⚛");
    const glyphMaterial = new THREE.SpriteMaterial({
      map: glyphTexture,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
    });

    for (let i = 0; i < 6; i++) {
      const sprite = new THREE.Sprite(glyphMaterial.clone());
      sprite.scale.set(0.6, 0.6, 0.6);
      glyphOrbitRef.current.add(sprite);
    }
  }, [container.glyph]);

  /** 🎛 Animate core, particles, and glyphs */
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (coreRef.current) {
      const mesh = coreRef.current as THREE.Mesh;
      mesh.rotation.y += 0.01;
      const mat = mesh.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 1.2 + Math.sin(t * 3) * 0.5;
    }

    if (latticeRef.current) {
      (latticeRef.current as THREE.Points).rotation.y -= 0.002;
    }

    if (pulseFieldRef.current) {
      const mesh = pulseFieldRef.current as THREE.Mesh;
      mesh.scale.setScalar(1 + 0.2 * Math.sin(t * 2));
      const mat = mesh.material as THREE.MeshStandardMaterial;
      mat.opacity = 0.25 + 0.15 * Math.sin(t * 2);
    }

    if (glyphOrbitRef.current) {
      const group = glyphOrbitRef.current as THREE.Group;
      group.children.forEach((glyph: any, i: number) => {
        const angle = t * 0.8 + (i * Math.PI) / 3;
        glyph.position.set(
          Math.cos(angle) * 2.5,
          Math.sin(angle * 1.2) * 1.2,
          Math.sin(angle) * 2.5
        );
        if (glyph.material instanceof THREE.SpriteMaterial) {
          glyph.material.opacity = 0.5 + Math.sin(t * 2 + i) * 0.4;
        }
      });
    }
  });

  return (
    <group position={position}>
      {/* 🌐 Quantum Core */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[0.6, 32, 32]} />
        <meshStandardMaterial
          color="#ff00ff"
          emissive="#ff33ff"
          emissiveIntensity={1.2}
          metalness={0.7}
          roughness={0.3}
          transparent
          opacity={0.9}
        />
      </mesh>

      {/* ✨ Lattice Particles */}
      <points ref={latticeRef} />

      {/* 🔥 Pulsing Energy Field */}
      <mesh ref={pulseFieldRef}>
        <sphereGeometry args={[2.8, 64, 64]} />
        <meshStandardMaterial
          color="#ff00ff"
          emissive="#ff33ff"
          emissiveIntensity={0.4}
          transparent
          opacity={0.25}
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
            color: "#ff00ff",
            textShadow: "0 0 10px #ff00ff",
          }}
        >
          ⚛ {container.name}
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
  ctx.fillStyle = "#ff00ff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(glyph, size / 2, size / 2);
  return new THREE.CanvasTexture(canvas);
}

export default QuantumOrdRenderer;