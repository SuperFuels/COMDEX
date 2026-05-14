"use client";
import React from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import AtomContainerWrapper from "@/components/Atoms/AtomContainerWrapper";
import type { AtomModel } from "@/types/atom";

export default function AtomScene({ atoms }: { atoms: AtomModel[] }) {
  return (
    <Canvas camera={{ position: [0, 2, 6], fov: 55 }}>
      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 10, 7]} intensity={0.8} />
      {atoms.map((a, i) => (
        <AtomContainerWrapper
          key={a.id}
          atom={a}
          position={a?.viz?.position ?? [i * 2 - 4, 0, 0]}
        />
      ))}
      <OrbitControls enableDamping />
    </Canvas>
  );
}