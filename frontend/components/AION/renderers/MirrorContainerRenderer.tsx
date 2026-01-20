"use client";

import React, { useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html as DreiHtml } from "@react-three/drei";

interface MirrorContainerRendererProps {
  position: [number, number, number];
  container: {
    id: string;
    name: string;
    glyph?: string;
    runtime_tick?: number;
    logic_depth?: number;
  };
}

const MirrorContainerRenderer: React.FC<MirrorContainerRendererProps> = ({
  position,
  container,
}) => {
  // loosen refs to avoid @types/three mismatch hell
  const coreRef = useRef<any>(null);
  const panelsRef = useRef<any>(null);
  const glyphEchoRef = useRef<any>(null);

  /** 🪞 Generate reflective panels */
  useEffect(() => {
    if (!panelsRef.current) return;
    panelsRef.current.clear();

    const panelGeom = new THREE.PlaneGeometry(2, 2);
    const mirrorMaterial = new THREE.MeshStandardMaterial({
      color: "#88ccff",
      metalness: 1,
      roughness: 0,
      envMapIntensity: 2,
      side: THREE.DoubleSide,
    });

    const angles: [number, number, number][] = [
      [0, 0, 0],
      [Math.PI / 2, 0, 0],
      [-Math.PI / 2, 0, 0],
      [0, Math.PI / 2, 0],
      [0, -Math.PI / 2, 0],
      [Math.PI, 0, 0],
    ];

    angles.forEach((rot) => {
      const panel = new THREE.Mesh(panelGeom, mirrorMaterial.clone());
      panel.rotation.set(rot[0], rot[1], rot[2]);
      panel.position.set(
        Math.sin(rot[1]) * 2,
        Math.sin(rot[0]) * 2,
        Math.cos(rot[1]) * 2
      );
      panelsRef.current.add(panel);
    });
  }, []);

  /** 🔮 Glyph Echo Trails (holograms behind glass) */
  useEffect(() => {
    if (!glyphEchoRef.current) return;
    glyphEchoRef.current.clear();

    const glyphTexture = createGlyphTexture(container.glyph || "🪞");
    const glyphMaterial = new THREE.SpriteMaterial({
      map: glyphTexture,
      transparent: true,
      opacity: 0.6,
      depthWrite: false,
    });

    for (let i = 0; i < 6; i++) {
      const sprite = new THREE.Sprite(glyphMaterial.clone());
      sprite.scale.set(0.6, 0.6, 0.6);
      glyphEchoRef.current.add(sprite);
    }
  }, [container.glyph]);

  /** 🌀 Animate panels, glyph echoes, and core distortion */
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (coreRef.current) {
      const mat = coreRef.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 0.8 + Math.sin(t * 4) * 0.4;
    }

    if (panelsRef.current) {
      panelsRef.current.rotation.y += 0.002;
      panelsRef.current.rotation.x = Math.sin(t * 0.3) * 0.1;
    }

    if (glyphEchoRef.current) {
      glyphEchoRef.current.children.forEach((glyph: any, i: number) => {
        const angle = t * 0.6 + (i * Math.PI) / 3;
        glyph.position.set(
          Math.cos(angle) * 2.5,
          Math.sin(angle * 1.5) * 1,
          Math.sin(angle) * 2.5
        );
        if (glyph.material instanceof THREE.SpriteMaterial) {
          glyph.material.opacity = 0.4 + Math.sin(t * 2 + i) * 0.3;
        }
      });
    }
  });

  return (
    <group position={position}>
      {/* 🪞 Core Reflective Sphere */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[1, 64, 64]} />
        <meshStandardMaterial
          color="#88ccff"
          emissive="#66ccff"
          emissiveIntensity={1.2}
          metalness={0.8}
          roughness={0.05}
          transparent
          opacity={0.9}
        />
      </mesh>

      {/* 🪞 Floating Mirror Panels */}
      <group ref={panelsRef} />

      {/* 🔮 Glyph Echo Trails */}
      <group ref={glyphEchoRef} />

      {/* 🏷 Label */}
      <DreiHtml distanceFactor={12}>
        <div
          style={{
            textAlign: "center",
            fontSize: "0.8rem",
            color: "#66ccff",
            textShadow: "0 0 8px #66ccff",
          }}
        >
          🪞 {container.name}
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
  ctx.fillStyle = "#88ccff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(glyph, size / 2, size / 2);
  return new THREE.CanvasTexture(canvas);
}

export default MirrorContainerRenderer;