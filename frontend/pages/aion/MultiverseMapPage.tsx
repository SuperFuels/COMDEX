// File: frontend/pages/aion/MultiverseMapPage.tsx

import React from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars, Environment } from "@react-three/drei";
import dynamic from "next/dynamic";
import ContainerMap3D from "@/components/AION/ContainerMap3D";

export default function MultiverseMapPage() {
  return (
    <div style={{ width: "100vw", height: "100vh", backgroundColor: "black" }}>
      <Canvas
        camera={{ position: [0, 10, 20], fov: 60 }}
        gl={{ antialias: false }}
        dpr={[1, 2]}
      >
        {/* Lighting */}
        <ambientLight intensity={0.4} />
        <pointLight position={[10, 10, 10]} intensity={1.2} />

        {/* Background and environment */}
        <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
        <Environment preset="sunset" />

        {/* Camera controls */}
        <OrbitControls enablePan={true} enableZoom={true} enableRotate={true} />

        {/* Core 3D container map */}
        <ContainerMap3D />
      </Canvas>
    </div>
  );
}