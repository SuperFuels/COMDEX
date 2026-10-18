'use client';

import { useState, useRef, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Stars, Environment } from '@react-three/drei';
import dynamic from 'next/dynamic';
import type { GetServerSideProps } from "next";

export const getServerSideProps: GetServerSideProps = async () => {
  return { props: {} };
};
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

const RADIO_BASE = process.env.NEXT_PUBLIC_RADIO_BASE || ''; // e.g. https://radio-node.yourdomain.com
const CONTAINER_NAV = (process.env.NEXT_PUBLIC_CONTAINER_NAV || 'site').toLowerCase(); // 'site' | 'spa'

function urlFrom(path: string) {
  // If you configured Next rewrite for /containers/* you can keep RADIO_BASE empty.
  return RADIO_BASE ? `${RADIO_BASE}${path}` : path;
}

async function fetchJson<T = any>(url: string): Promise<T> {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export default function MultiversePage() {
  const [layout, setLayout] = useState<LayoutType>('ring');
  const [activeContainer, setActiveContainer] = useState<string | null>(null);
  const [containers, setContainers] = useState<ContainerInfo[]>([]);
  const [homeContainerId, setHomeContainerId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        // Container ownership must be resolved by the authenticated backend;
        // the browser is not a durable identity registry.
        const data = await fetchJson<any[]>('/api/aion/containers/all');
        if (!cancelled && Array.isArray(data)) {
          const entries = data as ContainerInfo[];
          setContainers(entries);
          setHomeContainerId(
            entries.find((item) => /(?:^|__)home$/i.test(item.id))?.id ?? null,
          );
        }
      } catch (e: any) {
        console.warn('Multiverse load failed, fallback:', e?.message || e);
        try {
          const data = await fetchJson<any[]>('/api/aion/containers/all');
          if (!cancelled && Array.isArray(data)) setContainers(data as ContainerInfo[]);
        } catch (e2: any) {
          if (!cancelled) setErrMsg(`Failed to load containers (${e2?.message || e2})`);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const openContainer = (id: string) => {
    const preferSPA =
      CONTAINER_NAV === 'spa' ||
      (typeof window !== 'undefined' && ((window as any).__GNET_BROWSER__ || location.hash.startsWith('#/container')));

    if (preferSPA) {
      // Drive the SPA router (browser app)
      window.location.hash = `#/container/${encodeURIComponent(id)}`;
    } else {
      // Stay within website
      router.push(`/aion/container/${encodeURIComponent(id)}`);
    }
  };

  const handleTeleport = (id: string) => {
    setActiveContainer(id);
    // small delay for the camera glide effect
    setTimeout(() => openContainer(id), 600);
  };

  const goHome = () => {
    if (homeContainerId) openContainer(homeContainerId);
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

          <div className="flex items-center gap-2">
            <span className="opacity-80">Layout:</span>
            <select
              value={layout}
              onChange={(e) => setLayout(e.target.value as LayoutType)}
              className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-white"
            >
              <option value="sphere">Sphere</option>
              <option value="ring">Ring</option>
              <option value="grid">Grid</option>
            </select>
          </div>

          <div className="flex gap-2">
            <button
              onClick={goHome}
              disabled={!homeContainerId}
              className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 rounded text-white text-xs"
              title="Jump to your Home container"
            >
              🏠 Home
            </button>
            <a
              href="/aion/glyph-synthesis"
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-white text-xs"
            >
              ← Back to Synthesis Lab
            </a>
          </div>

          {loading && <div className="text-xs opacity-80">Loading containers…</div>}
          {errMsg && <div className="text-xs text-red-300">{errMsg}</div>}
        </div>

        {/* 3D Map */}
        <Canvas camera={{ position: [0, 10, 20], fov: 60 }}>
          <ambientLight intensity={0.4} />
          <pointLight position={[10, 10, 10]} intensity={1.2} />
          <Stars radius={100} depth={50} count={3500} factor={4} saturation={0} fade speed={1} />
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
      const size = Math.ceil(Math.sqrt(total || 1));
      const x = index % size;
      const z = Math.floor(index / size);
      return [x * 2 - size, 0, z * 2 - size];
    }
    if (layout === 'sphere') {
      const t = Math.max(1, total);
      const phi = Math.acos(-1 + (2 * index) / t);
      const theta = Math.sqrt(t * Math.PI) * phi;
      const r = 6;
      return [
        r * Math.cos(theta) * Math.sin(phi),
        r * Math.sin(theta) * Math.sin(phi),
        r * Math.cos(phi),
      ];
    }
    const angle = (index / Math.max(1, total)) * Math.PI * 2;
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
      camera.position.lerp({ x: x + 5, y: y + 4, z: z + 5 } as any, 0.05);
      camera.lookAt(x, y, z);
    }
  });

  return null;
}
