'use client';

import { useState, useRef, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Stars, Environment } from '@react-three/drei';
import dynamic from 'next/dynamic';

const ContainerMap3D = dynamic(() => import('@/components/AION/ContainerMap3D'), { ssr: false });

type LayoutType = 'ring' | 'grid' | 'sphere';

interface ContainerInfo {
  id: string;
  name: string;
  in_memory: boolean;
  connected: string[];
  glyph?: string;
  region?: string;
}

export default function MultiversePage() {
  const [layout, setLayout] = useState<LayoutType>('ring');
  const [activeContainer, setActiveContainer] = useState<string | null>(null);
  const [containers, setContainers] = useState<ContainerInfo[]>([]);
  const router = useRouter();

  useEffect(() => {
    fetch('/api/aion/containers/all')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setContainers(data);
        }
      })
      .catch(err => {
        console.warn('Failed to load containers:', err);
      });
  }, []);

  const handleTeleport = (id: string) => {
    console.log(`🌀 Teleporting to container: ${id}`);
    setActiveContainer(id);
    setTimeout(() => {
      router.push(`/aion/container/${id}`);
    }, 1000); // Delay for visual effect
  };

  return (
    <>
      <Head>
        <title>Multiverse Map • AION</title>
      </Head>

      <div className="w-screen h-screen bg-black relative overflow-hidden">
        {/* HUD Controls */}
        <div className="absolute top-4 left-4 z-10 space-y-3 bg-black/70 backdrop-blur-md p-4 rounded-xl shadow-md text-white text-sm">
          <div className="font-bold text-lg mb-1">🌌 Multiverse Map</div>
          <label className="block">
            Layout:
            <select
              value={layout}
              onChange={(e) => setLayout(e.target.value as LayoutType)}
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

        {/* 3D Map */}
        <Canvas camera={{ position: [0, 10, 20], fov: 60 }}>
          <ambientLight intensity={0.4} />
          <pointLight position={[10, 10, 10]} intensity={1.2} />
          <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
          <Environment preset="sunset" />

          <CameraEffects activeId={activeContainer} containers={containers} layout={layout} />

          <OrbitControls enablePan enableZoom enableRotate />
          <ContainerMap3D
            layout={layout}
            containers={containers}
            activeId={activeContainer ?? undefined}
            onTeleport={handleTeleport}
          />
        </Canvas>
      </div>
    </>
  );
}

function CameraEffects({
  activeId,
  containers,
  layout,
}: {
  activeId: string | null;
  containers: ContainerInfo[];
  layout: 'ring' | 'grid' | 'sphere';
}) {
  const { camera } = useThree();
  const targetRef = useRef<[number, number, number] | null>(null);

  // Compute fallback position from layout
  const getPosition = (
    index: number,
    total: number,
    layout: 'ring' | 'grid' | 'sphere'
  ): [number, number, number] => {
    if (layout === 'grid') {
      const size = Math.ceil(Math.sqrt(total));
      const x = index % size;
      const z = Math.floor(index / size);
      return [x * 2 - size, 0, z * 2 - size];
    }
    if (layout === 'sphere') {
      const phi = Math.acos(-1 + (2 * index) / total);
      const theta = Math.sqrt(total * Math.PI) * phi;
      const r = 6;
      return [
        r * Math.cos(theta) * Math.sin(phi),
        r * Math.sin(theta) * Math.sin(phi),
        r * Math.cos(phi),
      ];
    }
    const angle = (index / total) * Math.PI * 2;
    const radius = 6;
    const height = (index % 3) * 2;
    return [Math.cos(angle) * radius, height, Math.sin(angle) * radius];
  };

  useEffect(() => {
    if (activeId && containers.length > 0) {
      const index = containers.findIndex(c => c.id === activeId);
      if (index !== -1) {
        targetRef.current = getPosition(index, containers.length, layout);
      }
    }
  }, [activeId, containers, layout]);

  useFrame(() => {
    if (targetRef.current) {
      const [x, y, z] = targetRef.current;
      camera.position.lerp({ x: x + 5, y: y + 4, z: z + 5 }, 0.05);
      camera.lookAt(x, y, z);
    }
  });

  return null;
}