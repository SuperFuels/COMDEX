// frontend/components/GHX/atoms/electronOrbit.tsx
import React, { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Sphere, Html } from "@react-three/drei";
import * as THREE from "three";

type Electron = {
  meta?: {
    label?: string;
    linkContainerId?: string;
  };
};

type Shell = {
  radius: number;
  electrons: Electron[];
};

export function buildElectronShells(electronCount: number, electrons: Electron[]): Shell[] {
  const shells: Shell[] = [];
  const maxPerShell = 8;
  let remaining = electronCount;
  let index = 0;
  let shellIndex = 0;

  while (remaining > 0) {
    const count = Math.min(maxPerShell, remaining);
    const shellElectrons = electrons.slice(index, index + count);
    const radius = 1.4 + shellIndex * 0.6;
    shells.push({ radius, electrons: shellElectrons });

    remaining -= count;
    index += count;
    shellIndex += 1;
  }

  return shells;
}

type ElectronShellsProps = {
  center: [number, number, number];
  shells: Shell[];
  onTeleport?: (containerId: string) => void;
};

export const ElectronShells: React.FC<ElectronShellsProps> = ({ center, shells, onTeleport }) => {
  const groupRef = useRef<THREE.Group>(null);

  // 🌀 Continuous orbital rotation
  useFrame(() => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.0025;
    }
  });

  return (
    <group ref={groupRef}>
      {shells.map((shell, shellIdx) => {
        return shell.electrons.map((electron, i) => {
          const angle = (i / shell.electrons.length) * Math.PI * 2;
          const offsetY = Math.sin(angle + shellIdx) * 0.2; // 3D offset
          const x = center[0] + shell.radius * Math.cos(angle);
          const y = center[1] + offsetY;
          const z = center[2] + shell.radius * Math.sin(angle);

          const label = electron.meta?.label || "e⁻";
          const cid = electron.meta?.linkContainerId;

          return (
            <group key={`electron-${shellIdx}-${i}`} position={[x, y, z]}>
              <Sphere
                args={[0.08, 16, 16]}
                onClick={() => cid && onTeleport?.(cid)}
              >
                <meshStandardMaterial
                  color={"skyblue"}
                  emissive={"deepskyblue"}
                  emissiveIntensity={1.5}
                  toneMapped={false}
                />
              </Sphere>
              {/* Tooltip with label */}
              <Html center distanceFactor={6}>
                <div
                  style={{
                    background: "rgba(0,0,50,0.65)",
                    color: "white",
                    padding: "2px 6px",
                    borderRadius: "4px",
                    fontSize: "0.7rem",
                    whiteSpace: "nowrap",
                  }}
                >
                  {label}
                </div>
              </Html>
            </group>
          );
        });
      })}
    </group>
  );
};