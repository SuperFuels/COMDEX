// frontend/components/Hologram/ReplayBeamTrail.tsx
import React from "react";
import * as THREE from "three";
import { Html as DreiHtml } from '@react-three/drei';

interface ReplayBeamTrailProps {
  trail: [number, number, number][];
  type?: "collapsed" | "breakthrough" | "deadend";
  tick?: number;
}

const ReplayBeamTrail: React.FC<ReplayBeamTrailProps> = ({
  trail,
  type = "collapsed",
  tick,
}) => {
  const color =
    type === "breakthrough"
      ? "#10b981"
      : type === "deadend"
      ? "#ef4444"
      : "#6366f1";

  const points = trail.map((p) => new THREE.Vector3(...p));
  const geometry = new THREE.BufferGeometry().setFromPoints(points);

  return (
    <>
      <line>
        <primitive object={geometry} attach="geometry" />
        <lineDashedMaterial
          attach="material"
          color={color}
          linewidth={2}
          dashSize={0.1}
          gapSize={0.05}
          transparent
          opacity={0.9}
        />
      </line>

      {/* Optional Tick Label */}
      {tick !== undefined && (
        <DreiHtml position={points[Math.floor(points.length / 2)]}>
          <div className="text-[10px] text-white bg-black/80 px-2 py-1 rounded shadow">
            ⏪ Tick {tick}
          </div>
        </DreiHtml>
      )}
    </>
  );
};

export default ReplayBeamTrail;