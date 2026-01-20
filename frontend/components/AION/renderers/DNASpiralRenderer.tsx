"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html as DreiHtml } from "@react-three/drei";

interface DNASpiralRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    glyph?: string;
    logic_depth?: number;
    runtime_tick?: number;
  };
}

const DNASpiralRenderer: React.FC<DNASpiralRendererProps> = ({
  position,
  container,
}) => {
  // use any-typed refs to avoid @types/three vs three mismatch
  const helixRef = useRef<any>(null);
  const fieldRef = useRef<any>(null);
  const glyphGroupRef = useRef<any>(null);

  /** 🧬 Generate helix base pairs dynamically */
  useEffect(() => {
    if (!helixRef.current) return;
    helixRef.current.clear();

    const segments = 20;
    const radius = 0.6;
    const height = 4;

    const colors = ["#00f0ff", "#ff00ff", "#00ff88", "#ffaa00"];

    for (let i = 0; i < segments; i++) {
      const angle = (i / segments) * Math.PI * 10;
      const y = (i / segments - 0.5) * height;

      const left = new THREE.Mesh(
        new THREE.SphereGeometry(0.12, 16, 16),
        new THREE.MeshStandardMaterial({
          color: colors[i % colors.length],
          emissive: colors[i % colors.length],
          emissiveIntensity: 2,
        })
      );
      left.position.set(
        Math.cos(angle) * radius,
        y,
        Math.sin(angle) * radius
      );

      const right = new THREE.Mesh(
        new THREE.SphereGeometry(0.12, 16, 16),
        new THREE.MeshStandardMaterial({
          color: colors[(i + 1) % colors.length],
          emissive: colors[(i + 1) % colors.length],
          emissiveIntensity: 2,
        })
      );
      right.position.set(
        -Math.cos(angle) * radius,
        y,
        -Math.sin(angle) * radius
      );

      const bond = new THREE.Mesh(
        new THREE.CylinderGeometry(0.025, 0.025, radius * 2, 8),
        new THREE.MeshStandardMaterial({
          color: "#ffffff",
          emissive: "#ffffff",
          emissiveIntensity: 1.2,
        })
      );
      bond.position.set(0, y, 0);
      bond.rotation.z = Math.PI / 2;

      helixRef.current.add(left, right, bond);
    }
  }, []);

  /** 🌌 Glyph holograms orbiting around the DNA */
  useEffect(() => {
    if (!glyphGroupRef.current) return;
    glyphGroupRef.current.clear();

    const glyphMaterial = new THREE.SpriteMaterial({
      map: createGlyphTexture(container.glyph || "🧬"),
      transparent: true,
      opacity: 0.8,
      depthWrite: false,
    });

    for (let i = 0; i < 8; i++) {
      const sprite = new THREE.Sprite(glyphMaterial.clone());
      sprite.position.set(1.5, (i / 8) * 3 - 1.5, 0);
      sprite.scale.set(0.6, 0.6, 0.6);
      glyphGroupRef.current.add(sprite);
    }
  }, [container.glyph]);

  /** 🎥 Animations */
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (helixRef.current) {
      helixRef.current.rotation.y = t * 0.5;
    }

    if (fieldRef.current) {
      fieldRef.current.rotation.y = -t * 0.2;
    }

    if (glyphGroupRef.current) {
      const children = glyphGroupRef.current.children;
      children.forEach((child: any, i: number) => {
        const angle = t * 0.8 + (i * Math.PI) / 4;
        child.position.x = Math.cos(angle) * 2;
        child.position.z = Math.sin(angle) * 2;
      });
    }
  });

  return (
    <group position={position}>
      {/* 🧬 DNA Helix */}
      <group ref={helixRef} />

      {/* 🌌 Energy Field */}
      <mesh ref={fieldRef}>
        <torusGeometry args={[2.2, 0.05, 16, 64]} />
        <meshStandardMaterial
          color="#00ffff"
          emissive="#00ffff"
          emissiveIntensity={0.8}
          transparent
          opacity={0.5}
        />
      </mesh>

      {/* 🔮 Orbiting glyph holograms */}
      <group ref={glyphGroupRef} />

      {/* 📛 Label */}
      <DreiHtml distanceFactor={12}>
        <div
          style={{
            textAlign: "center",
            fontSize: "0.8rem",
            color: "#00f0ff",
            textShadow: "0 0 8px #00f0ff",
          }}
        >
          🧬 {container.name}
        </div>
      </DreiHtml>
    </group>
  );
};

/** 🖌️ Procedural glyph texture generator */
function createGlyphTexture(glyph: string): THREE.Texture {
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "rgba(0,0,0,0)";
  ctx.fillRect(0, 0, size, size);
  ctx.font = "bold 90px sans-serif";
  ctx.fillStyle = "#00f0ff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(glyph, size / 2, size / 2);
  return new THREE.CanvasTexture(canvas);
}

export default DNASpiralRenderer;