'use client';

import { useEffect, useRef, useState } from 'react';
import { Html, Line } from '@react-three/drei';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface Zone {
  id: string;
  name: string;
  position: [number, number, number];
  layer: 'inner' | 'outer' | 'deep';
}

interface WarpDriveNavigatorProps {
  zones: Zone[];
  onWarpComplete?: (zoneId: string) => void;
}

export default function WarpDriveNavigator({ zones, onWarpComplete }: WarpDriveNavigatorProps) {
  const { camera } = useThree();
  const [zone, setZone] = useState<string>(zones[0]?.id || '');
  const [isWarping, setIsWarping] = useState(false);
  const [warpProgress, setWarpProgress] = useState(0);
  const [warpTrail, setWarpTrail] = useState<[number, number, number][]>([]);
  const [warpStartPos, setWarpStartPos] = useState<[number, number, number] | null>(null);
  const [warpEndPos, setWarpEndPos] = useState<[number, number, number] | null>(null);
  const [scannerSweep, setScannerSweep] = useState(0);

  const targetRef = useRef<[number, number, number] | null>(null);

  // 🔑 Hotkey Warp (keys 1–4 to jump between zones quickly)
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (['1', '2', '3', '4'].includes(e.key)) {
        const idx = parseInt(e.key) - 1;
        if (zones[idx]) initiateWarp(zones[idx].id);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [zones]);

  // 🌌 Initiate warp to selected zone
  const initiateWarp = (newZoneId: string) => {
    const currentPos = zones.find((z) => z.id === zone)?.position || [0, 0, 0];
    const targetPos = zones.find((z) => z.id === newZoneId)?.position || [0, 0, 0];

    setWarpStartPos(currentPos);
    setWarpEndPos(targetPos);
    setWarpTrail((prev) => [...prev.slice(-2), currentPos]); // Keep last 3 trails
    setIsWarping(true);
    setWarpProgress(0);
    setZone(newZoneId);

    const interval = setInterval(() => {
      setWarpProgress((p) => {
        if (p >= 100) {
          clearInterval(interval);
          setIsWarping(false);
          onWarpComplete?.(newZoneId);
          return 100;
        }
        return p + 4;
      });
    }, 50);
  };

  // 🔭 Scanner sweep & smooth camera follow
  useFrame(() => {
    if (!isWarping) setScannerSweep((s) => (s + 0.02) % (Math.PI * 2));
    if (targetRef.current) {
      const [x, y, z] = targetRef.current;
      camera.position.lerp({ x: x + 5, y: y + 4, z: z + 5 }, 0.05);
      camera.lookAt(x, y, z);
    }
  });

  useEffect(() => {
    const zonePos = zones.find((z) => z.id === zone)?.position;
    if (zonePos) targetRef.current = zonePos;
  }, [zone]);

  return (
    <>
      {/* 🚀 Warp Trail Lines */}
      {warpTrail.map((pos, idx) =>
        idx < warpTrail.length - 1 && (
          <Line
            key={idx}
            points={[warpTrail[idx], warpTrail[idx + 1]]}
            color="#ffaa00"
            lineWidth={1.5}
            transparent
            opacity={0.5}
          />
        )
      )}

      {/* 🌌 Warp Arc Visualization */}
      {isWarping && warpStartPos && warpEndPos && (
        <WarpArc start={warpStartPos} end={warpEndPos} />
      )}

      {/* 🛸 Zone Beacons */}
      {zones.map((z) => (
        <ZoneBeacon
          key={z.id}
          zone={z}
          onClick={() => initiateWarp(z.id)}
          scannerSweep={scannerSweep}
        />
      ))}

      {/* HUD Overlay during Warp */}
      {isWarping && (
        <Html fullscreen>
          <div className="flex flex-col items-center justify-center w-full h-full bg-black/90 text-white z-50">
            <div className="text-3xl animate-pulse mb-4">🚀 Warp Drive Engaged: {zone}</div>
            <div className="w-2/3 bg-gray-800 h-4 rounded-full overflow-hidden">
              <div
                className="bg-blue-500 h-full transition-all duration-100"
                style={{ width: `${warpProgress}%` }}
              />
            </div>
          </div>
        </Html>
      )}
    </>
  );
}

/* 🌠 Warp Arc (Curved Flight Path) */
function WarpArc({ start, end }: { start: [number, number, number]; end: [number, number, number] }) {
  const mid: [number, number, number] = [
    (start[0] + end[0]) / 2,
    (start[1] + end[1]) / 2 + 8,
    (start[2] + end[2]) / 2,
  ];
  return (
    <Line
      points={[start, mid, end]}
      color="#00f0ff"
      lineWidth={3}
      dashed
      dashSize={0.3}
      gapSize={0.2}
    />
  );
}

/* 🛸 Zone Beacon + Scanner Rings */
function ZoneBeacon({
  zone,
  onClick,
  scannerSweep,
}: {
  zone: Zone;
  onClick: () => void;
  scannerSweep: number;
}) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (ref.current) ref.current.scale.setScalar(1 + 0.15 * Math.sin(clock.elapsedTime * 2));
  });
  return (
    <group position={zone.position} onClick={onClick}>
      <mesh ref={ref}>
        <sphereGeometry args={[0.8, 32, 32]} />
        <meshStandardMaterial
          color="#00f0ff"
          emissive="#00f0ff"
          emissiveIntensity={2}
          transparent
          opacity={0.6}
        />
      </mesh>
      {/* Rotating Scanner Ring */}
      <mesh rotation={[0, scannerSweep, 0]}>
        <torusGeometry args={[2, 0.05, 16, 64]} />
        <meshStandardMaterial
          color="#ff00ff"
          emissive="#aa00ff"
          emissiveIntensity={0.8}
          transparent
          opacity={0.4}
        />
      </mesh>
      <Html distanceFactor={12}>
        <div className="text-center text-white text-sm bg-black/50 px-2 py-1 rounded cursor-pointer">
          🚀 {zone.name}
        </div>
      </Html>
    </group>
  );
}