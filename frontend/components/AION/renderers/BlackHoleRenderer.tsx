"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";

interface BlackHoleRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    glyph?: string;
    logic_depth?: number;
    runtime_tick?: number;
  };
}

const BlackHoleRenderer: React.FC<BlackHoleRendererProps> = ({ position, container }) => {
  const coreRef = useRef<THREE.Mesh>(null);
  const diskRef = useRef<THREE.Mesh>(null);
  const debrisGroupRef = useRef<THREE.Group>(null);

  // Create debris glyphs swirling around
  useEffect(() => {
    if (!debrisGroupRef.current) return;
    debrisGroupRef.current.clear();
    const glyphCount = 12;
    const glyphMaterial = new THREE.SpriteMaterial({
      map: createGlyphTexture(container.glyph || "↯"),
      transparent: true,
      opacity: 0.8,
      depthWrite: false,
      depthTest: true,
    });
    for (let i = 0; i < glyphCount; i++) {
      const sprite = new THREE.Sprite(glyphMaterial.clone());
      const radius = 3 + Math.random() * 2;
      sprite.position.set(radius, 0, 0);
      sprite.scale.set(0.8, 0.8, 0.8);
      debrisGroupRef.current.add(sprite);
    }
  }, [container.glyph]);

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    // Pulsating singularity core
    if (coreRef.current) {
      const scale = 1 + Math.sin(t * 5) * 0.15;
      coreRef.current.scale.set(scale, scale, scale);
    }

    // Rotating accretion disk
    if (diskRef.current) {
      diskRef.current.rotation.y += 0.002;
    }

    // Orbiting glyph debris
    if (debrisGroupRef.current) {
      debrisGroupRef.current.children.forEach((child, i) => {
        const angle = t * 0.5 + i * (Math.PI * 2) / debrisGroupRef.current!.children.length;
        const radius = 3.5 + Math.sin(t + i) * 0.5;
        child.position.set(Math.cos(angle) * radius, Math.sin(t * 2 + i) * 0.2, Math.sin(angle) * radius);
        (child as THREE.Sprite).material.opacity = 0.7 + 0.3 * Math.sin(t * 2 + i);
      });
    }
  });

  return (
    <group position={position}>
      {/* Core singularity */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[0.6, 64, 64]} />
        <shaderMaterial
          vertexShader={lensVertexShader}
          fragmentShader={lensFragmentShader}
          uniforms={{
            time: { value: 0 },
            glowColor: { value: new THREE.Color("#000000") },
          }}
          transparent
          depthWrite={false}
        />
      </mesh>

      {/* Accretion Disk */}
      <mesh ref={diskRef} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[2.5, 0.2, 32, 256]} />
        <meshStandardMaterial
          color="#ff5500"
          emissive="#ff2200"
          emissiveIntensity={2.5}
          metalness={0.8}
          roughness={0.2}
        />
      </mesh>

      {/* Glyph debris swirling */}
      <group ref={debrisGroupRef} />

      {/* Floating label */}
      <Html distanceFactor={12}>
        <div
          style={{
            textAlign: "center",
            fontSize: "0.8rem",
            color: "white",
            textShadow: "0 0 6px #ff2200",
          }}
        >
          🕳 {container.name}
        </div>
      </Html>
    </group>
  );
};

/** 🌀 Simple procedural glyph texture generator */
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

/** 🎨 Vertex shader for gravitational lensing distortion */
const lensVertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

/** 🌌 Fragment shader for black hole glow + lensing */
const lensFragmentShader = `
  uniform float time;
  uniform vec3 glowColor;
  varying vec2 vUv;
  void main() {
    float dist = distance(vUv, vec2(0.5));
    float lens = smoothstep(0.45, 0.0, dist) * 0.8;
    vec3 color = mix(glowColor, vec3(0.0), lens);
    gl_FragColor = vec4(color, 1.0 - dist * 1.5);
  }
`;

export default BlackHoleRenderer;