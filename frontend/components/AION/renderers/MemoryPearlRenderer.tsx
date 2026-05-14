"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html as DreiHtml } from "@react-three/drei";

interface MemoryPearlRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    glyph?: string;
    logic_depth?: number;
    runtime_tick?: number;
  };
}

const MemoryPearlRenderer: React.FC<MemoryPearlRendererProps> = ({
  position,
  container,
}) => {
  // loosen refs to any to avoid @types/three mismatch
  const pearlRef = useRef<any>(null);
  const rippleGroupRef = useRef<any>(null);
  const glyphRingRef = useRef<any>(null);

  /** 🔮 Glyph Rings (Orbiting Holograms) */
  useEffect(() => {
    if (!glyphRingRef.current) return;
    glyphRingRef.current.clear();

    const glyphTexture = createGlyphTexture(container.glyph || "◉");
    const glyphMaterial = new THREE.SpriteMaterial({
      map: glyphTexture,
      transparent: true,
      opacity: 0.8,
    });

    const count = 10;
    for (let i = 0; i < count; i++) {
      const sprite = new THREE.Sprite(glyphMaterial.clone());
      sprite.scale.set(0.4, 0.4, 0.4);
      glyphRingRef.current.add(sprite);
    }
  }, [container.glyph]);

  /** 🌊 Energy Ripple Rings */
  useEffect(() => {
    if (!rippleGroupRef.current) return;
    rippleGroupRef.current.clear();

    for (let i = 0; i < 3; i++) {
      const ripple = new THREE.Mesh(
        new THREE.RingGeometry(1.5 + i * 0.6, 1.6 + i * 0.6, 64),
        new THREE.MeshBasicMaterial({
          color: "#00ffff",
          transparent: true,
          opacity: 0.25,
          side: THREE.DoubleSide,
        })
      );
      ripple.rotation.x = Math.PI / 2;
      rippleGroupRef.current.add(ripple);
    }
  }, []);

  /** 🌀 Animations (Pearl floating, ripple expansion, glyph orbiting) */
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    // Pearl bob + emissive pulse
    if (pearlRef.current) {
      pearlRef.current.position.y = Math.sin(t * 1.5) * 0.2;
      const mat = pearlRef.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 1.2 + Math.sin(t * 3) * 0.8;
    }

    // Ripple ring growth + fade
    if (rippleGroupRef.current) {
      rippleGroupRef.current.children.forEach((obj: any, i: number) => {
        obj.scale.setScalar(1 + ((t + i) % 2) * 0.5);

        if (
          obj instanceof THREE.Mesh &&
          obj.material instanceof THREE.MeshBasicMaterial
        ) {
          obj.material.opacity = 0.25 * (1 - ((t + i) % 2) * 0.8);
        }
      });
    }

    // Glyph sprites orbit
    if (glyphRingRef.current) {
      const total = glyphRingRef.current.children.length || 1;
      glyphRingRef.current.children.forEach((child: any, i: number) => {
        const angle = t * 0.5 + (i * Math.PI * 2) / total;
        child.position.set(
          Math.cos(angle) * 2.5,
          Math.sin(angle * 1.3) * 1,
          Math.sin(angle) * 2.5
        );
      });
    }
  });

  return (
    <group position={position}>
      {/* 🌑 Floating Pearl Core */}
      <mesh ref={pearlRef}>
        <sphereGeometry args={[1.2, 64, 64]} />
        <meshStandardMaterial
          color="#ffffff"
          emissive="#00faff"
          emissiveIntensity={1.5}
          roughness={0.1}
          metalness={0.4}
          transparent
          opacity={0.95}
        />
      </mesh>

      {/* 🌊 Ripple Energy Rings */}
      <group ref={rippleGroupRef} />

      {/* 🔮 Glyph Orbiting Rings */}
      <group ref={glyphRingRef} />

      {/* 🏷 Label */}
      <DreiHtml distanceFactor={12}>
        <div
          style={{
            textAlign: "center",
            fontSize: "0.8rem",
            color: "#00f8ff",
            textShadow: "0 0 8px #00f8ff",
          }}
        >
          ◉ {container.name}
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

export default MemoryPearlRenderer;