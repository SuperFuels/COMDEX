// File: frontend/components/AION/PulseFlowParticles.tsx

import React, { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import { BufferGeometry, Points, PointsMaterial, Vector3 } from "three";

interface PulseFlowProps {
  start: [number, number, number];
  end: [number, number, number];
  count?: number;
  speed?: number;
  color?: string;
}

export default function PulseFlowParticles({
  start,
  end,
  count = 10,
  speed = 1,
  color = "#66f",
}: PulseFlowProps) {
  const pointsRef = useRef<Points>(null!);
  const baseDirection = useMemo(() => {
    const from = new Vector3(...start);
    const to = new Vector3(...end);
    return new Vector3().subVectors(to, from).normalize();
  }, [start, end]);

  const offsets = useMemo(() => {
    return Array.from({ length: count }, (_, i) => i / count);
  }, [count]);

  const positions = useMemo(() => {
    const from = new Vector3(...start);
    const to = new Vector3(...end);
    const dir = new Vector3().subVectors(to, from);
    return offsets.map(offset => {
      const point = new Vector3().copy(from).addScaledVector(dir, offset);
      return point;
    });
  }, [start, end, offsets]);

  const geometry = useMemo(() => {
    const geo = new BufferGeometry();
    const posArray = new Float32Array(positions.length * 3);
    positions.forEach((p, i) => {
      posArray[i * 3] = p.x;
      posArray[i * 3 + 1] = p.y;
      posArray[i * 3 + 2] = p.z;
    });
    geo.setAttribute("position", new THREE.BufferAttribute(posArray, 3));
    return geo;
  }, [positions]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const move = (t * speed) % 1;

    const from = new Vector3(...start);
    const to = new Vector3(...end);
    const dir = new Vector3().subVectors(to, from);

    const posAttr = geometry.getAttribute("position") as THREE.BufferAttribute;
    offsets.forEach((offset, i) => {
      const rel = (offset + move) % 1;
      const p = new Vector3().copy(from).addScaledVector(dir, rel);
      posAttr.setXYZ(i, p.x, p.y, p.z);
    });
    posAttr.needsUpdate = true;
  });

  return (
    <points ref={pointsRef} geometry={geometry}>
      <pointsMaterial color={color} size={0.1} sizeAttenuation transparent />
    </points>
  );
}