"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";

interface VortexRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    glyph?: string;
    runtime_tick?: number;
    logic_depth?: number;
  };
}

const VortexRenderer: React.FC<VortexRendererProps> = ({ position, container }) => {
  // loosen refs to avoid @types/three generic mismatch
  const funnelRef = useRef<any>(null);
  const swirlParticlesRef = useRef<any>(null);
  const glyphOrbitRef = useRef<any>(null);
  const distortionRef = useRef<any>(null);

  /** 🌌 Swirl Particles Setup */
  useEffect(() => {
    const particles = 400;
    const positions = new Float32Array(particles * 3);

    for (let i = 0; i < particles; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = Math.random() * 4;
      const height = Math.random() * 6 - 3;
      positions[i * 3 + 0] = Math.cos(angle) * radius;
      positions[i * 3 + 1] = height;
      positions[i * 3 + 2] = Math.sin(angle) * radius;
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));

    const mat = new THREE.PointsMaterial({
      color: "#00ffff",
      size: 0.06,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
    });

    swirlParticlesRef.current = new THREE.Points(geo, mat);

    return () => {
      geo.dispose();
      mat.dispose();
    };
  }, []);

  /** 🔮 Glyph Orbit Projectors */
  useEffect(() => {
    if (!glyphOrbitRef.current) return;
    const group = glyphOrbitRef.current as THREE.Group;
    group.clear();

    const glyphTexture = createGlyphTexture(container.glyph || "🌀");
    const glyphMaterial = new THREE.SpriteMaterial({
      map: glyphTexture,
      transparent: true,
      opacity: 0.9,
      depthWrite: false,
    });

    for (let i = 0; i < 5; i++) {
      const sprite = new THREE.Sprite(glyphMaterial.clone());
      sprite.scale.set(0.5, 0.5, 0.5);
      group.add(sprite);
    }
  }, [container.glyph]);

  /** 🎛 Animations */
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (funnelRef.current) {
      const mesh = funnelRef.current as THREE.Mesh;
      mesh.rotation.y += 0.02;
      const mat = mesh.material as THREE.MeshStandardMaterial;
      mat.opacity = 0.3 + Math.sin(t * 3) * 0.1;
    }

    if (swirlParticlesRef.current) {
      const pts = swirlParticlesRef.current as THREE.Points;
      pts.rotation.y -= 0.01;
    }

    if (distortionRef.current) {
      const mesh = distortionRef.current as THREE.Mesh;
      mesh.scale.setScalar(1 + 0.15 * Math.sin(t * 2));
      const mat = mesh.material as THREE.MeshStandardMaterial;
      mat.opacity = 0.2 + Math.sin(t * 2.5) * 0.1;
    }

    if (glyphOrbitRef.current) {
      const group = glyphOrbitRef.current as THREE.Group;
      const len = group.children.length || 1;
      group.children.forEach((glyph, i) => {
        const angle = t * 0.6 + (i * Math.PI) / 2;
        glyph.position.set(
          Math.cos(angle) * 3,
          Math.sin(angle) * 1.5,
          Math.sin(angle) * 3
        );
        const mat = (glyph as THREE.Sprite).material as THREE.SpriteMaterial;
        mat.opacity = 0.6 + Math.sin(t * 3 + i) * 0.3;
      });
    }
  });

  return (
    <group position={position}>
      {/* 🔵 Energy Funnel */}
      <mesh ref={funnelRef} rotation={[Math.PI, 0, 0]}>
        <coneGeometry args={[3.5, 6, 64, 32, true]} />
        <meshStandardMaterial
          color="#00ffff"
          emissive="#00ffff"
          emissiveIntensity={2}
          transparent
          opacity={0.4}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* 🌌 Swirling Particles */}
      {swirlParticlesRef.current && <primitive object={swirlParticlesRef.current} />}

      {/* ✨ Distortion Field */}
      <mesh ref={distortionRef}>
        <sphereGeometry args={[4.5, 64, 64]} />
        <meshStandardMaterial
          color="#00ffff"
          emissive="#00ffff"
          emissiveIntensity={0.4}
          transparent
          opacity={0.25}
          side={THREE.BackSide}
        />
      </mesh>

      {/* 🔮 Glyph Orbit */}
      <group ref={glyphOrbitRef} />

      {/* 🏷 Label */}
      <Html distanceFactor={12}>
        <div
          style={{
            textAlign: "center",
            fontSize: "0.8rem",
            color: "#00ffff",
            textShadow: "0 0 12px #00f0ff",
          }}
        >
          🌀 {container.name}
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

export default VortexRenderer;