// File: pages/aion/multiverse.tsx
'use client';

import { useState } from 'react';
import Head from 'next/head';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars, Environment } from '@react-three/drei';
import dynamic from 'next/dynamic';

const ContainerMap3D = dynamic(() => import('@/components/AION/ContainerMap3D'), { ssr: false });

export default function MultiversePage() {
  const [layout, setLayout] = useState<'ring' | 'grid' | 'sphere'>('ring');

  return (
    <>
      <Head>
        <title>Multiverse Map • AION</title>
      </Head>

      <div className="w-screen h-screen bg-black relative overflow-hidden">
        {/* HUD */}
        <div className="absolute top-4 left-4 z-10 space-y-3 bg-black/70 backdrop-blur-md p-4 rounded-xl shadow-md text-white text-sm">
          <div className="font-bold text-lg mb-1">🌌 Multiverse Map</div>
          <label className="block">
            Layout:
            <select
              value={layout}
              onChange={(e) => setLayout(e.target.value as any)}
              className="ml-2 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-white"
            >
              <option value="sphere">Sphere</option>
              <option value="ring">Ring</option>
              <option value="grid">Grid</option>
            </select>
          </label>
          <a
            href="/aion/glyph-synthesis"
            className="inline-block mt-3 px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-white text-xs"
          >
            ← Back to Synthesis Lab
          </a>
        </div>

        {/* 3D Map Canvas */}
        <Canvas camera={{ position: [0, 10, 20], fov: 60 }}>
          <ambientLight intensity={0.4} />
          <pointLight position={[10, 10, 10]} intensity={1.2} />
          <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
          <Environment preset="sunset" />
          <OrbitControls enablePan enableZoom enableRotate />
          <ContainerMap3D layout={layout} />
        </Canvas>
      </div>
    </>
  );
}