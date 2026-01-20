'use client';

import { useEffect, useRef, useState } from "react";
import { Html as DreiHtml } from "@react-three/drei";
import { useThree, useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface Zone {
  id: string;
  name: string;
  position: [number, number, number];
  layer: "inner" | "outer" | "deep";
}

interface WarpDriveNavigatorProps {
  zones: Zone[];
  onWarpComplete?: (zoneId: string) => void;
}

export default function WarpDriveNavigator({
  zones,
  onWarpComplete,
}: WarpDriveNavigatorProps) {
  const { camera } = useThree();
  const [zone, setZone] = useState<string>(zones[0]?.id || "");
  const [isWarping, setIsWarping] = useState(false);
  const [warpProgress, setWarpProgress] = useState(0);
  const [warpTrail, setWarpTrail] = useState<[number, number, number][]>([]);
  const [warpStartPos, setWarpStartPos] = useState<[number, number, number] | null>(null);
  const [warpEndPos, setWarpEndPos] = useState<[number, number, number] | null>(null);
  const [scannerSweep, setScannerSweep] = useState(0);

  const targetRef = useRef<[number, number, number] | null>(null);

  // 1–4 hotkeys to warp
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (["1", "2", "3", "4"].includes(e.key)) {
        const idx = parseInt(e.key) - 1;
        if (zones[idx]) initiateWarp(zones[idx].id);
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [zones]);

  const initiateWarp = (newZoneId: string) => {
    const currentPos = zones.find((z) => z.id === zone)?.position || [0, 0, 0];
    const targetPos = zones.find((z) => z.id === newZoneId)?.position || [0, 0, 0];

    setWarpStartPos(currentPos);
    setWarpEndPos(targetPos);
    setWarpTrail((prev) => [...prev.slice(-2), currentPos]); // keep last 3 points
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

  // camera follow + scanner sweep
  useFrame(() => {
    if (!isWarping) setScannerSweep((s) => (s + 0.02) % (Math.PI * 2));
    if (targetRef.current) {
      const [x, y, z] = targetRef.current;
      camera.position.lerp({ x: x + 5, y: y + 4, z: z + 5 } as any, 0.05);
      camera.lookAt(x, y, z);
    }
  });

  useEffect(() => {
    const zonePos = zones.find((z) => z.id === zone)?.position;
    if (zonePos) targetRef.current = zonePos;
  }, [zone, zones]);

  return (
    <>
      {/* 🚀 Warp Trail (native three.js line segments) */}
      {warpTrail.slice(0, -1).map((p, idx) => {
        const next = warpTrail[idx + 1];
        const positions = new Float32Array([
          p[0],
          p[1],
          p[2],
          next[0],
          next[1],
          next[2],
        ]);
        return (
          <line key={idx}>
            <bufferGeometry>
              <bufferAttribute
                attach="attributes-position"
                array={positions}
                count={2}
                itemSize={3}
              />
            </bufferGeometry>
            <lineBasicMaterial color="#ffaa00" transparent opacity={0.5} />
          </line>
        );
      })}

      {/* 🌌 Warp Arc */}
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

      {/* HUD during warp */}
      {isWarping && (
        <DreiHtml fullscreen>
          <div className="flex flex-col items-center justify-center w-full h-full bg-black/90 text-white z-50">
            <div className="text-3xl animate-pulse mb-4">
              🚀 Warp Drive Engaged: {zone}
            </div>
            <div className="w-2/3 bg-gray-800 h-4 rounded-full overflow-hidden">
              <div
                className="bg-blue-500 h-full transition-all duration-100"
                style={{ width: `${warpProgress}%` }}
              />
            </div>
          </div>
        </DreiHtml>
      )}
    </>
  );
}

/* 🌠 Warp Arc (Curved Flight Path) */
function WarpArc({
  start,
  end,
}: {
  start: [number, number, number];
  end: [number, number, number];
}) {
  const mid: [number, number, number] = [
    (start[0] + end[0]) / 2,
    (start[1] + end[1]) / 2 + 8,
    (start[2] + end[2]) / 2,
  ];

  const points = [
    new THREE.Vector3(...start),
    new THREE.Vector3(...mid),
    new THREE.Vector3(...end),
  ];
  const positions = new Float32Array(points.flatMap((p) => [p.x, p.y, p.z]));

  return (
    <line>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          array={positions}
          count={points.length}
          itemSize={3}
        />
      </bufferGeometry>
      <lineBasicMaterial color="#00f0ff" transparent opacity={0.8} />
    </line>
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
  // 🧨 kill three’s generic typing – use any + cast in JSX
  const ref = useRef<any>(null);

  useFrame(({ clock }) => {
    if (ref.current) {
      const s = 1 + 0.15 * Math.sin(clock.elapsedTime * 2);
      ref.current.scale.setScalar(s);
    }
  });

  return (
    <group position={zone.position} onClick={onClick}>
      <mesh ref={ref as any}>
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

      <DreiHtml distanceFactor={12}>
        <div className="text-center text-white text-sm bg-black/50 px-2 py-1 rounded cursor-pointer">
          🚀 {zone.name}
        </div>
      </DreiHtml> 
    </group>
  );
}