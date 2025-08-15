import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { Html } from '@react-three/drei';

// Helper: convert soulHash or identity into color hue
function soulHashToHue(soulHash: string): number {
  let hash = 0;
  for (let i = 0; i < soulHash.length; i++) {
    hash = soulHash.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash % 360);
}

export default function GHXSignatureTrail({
  identity = "GHXNode.identity",
  radius = 2.2,
  speed = 1,
}: {
  identity?: string;
  radius?: number;
  speed?: number;
}) {
  const trailRef = useRef<any>();

  // Derive color from soul identity
  const hue = soulHashToHue(identity);
  const color = new THREE.Color(`hsl(${hue}, 80%, 60%)`);

  useFrame(({ clock }) => {
    if (trailRef.current) {
      const t = clock.getElapsedTime();
      const x = radius * Math.cos(t * speed);
      const z = radius * Math.sin(t * speed);
      trailRef.current.position.set(x, 0, z);
      trailRef.current.rotation.y = t * speed;
    }
  });

  return (
    <mesh ref={trailRef}>
      <torusGeometry args={[0.2, 0.05, 16, 100]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={1.5} />
      <Html center>
        <div style={{
          color: color.getStyle(),
          fontSize: "0.9em",
          fontWeight: "bold",
          opacity: 0.9,
          textShadow: "0 0 4px rgba(255,255,255,0.5)",
        }}>
          🧬
        </div>
      </Html>
    </mesh>
  );
}