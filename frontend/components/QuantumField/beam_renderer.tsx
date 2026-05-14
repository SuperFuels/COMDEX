"use client";

import React, { useRef, useMemo } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

export interface BeamProps {
  source: [number, number, number];
  target: [number, number, number];
  path?: [number, number, number][]; // optional explicit path
  prediction?: boolean;
  collapseState?: "collapsed" | "predicted" | "contradicted";
  sqiScore?: number;
  show?: boolean;
  emotion?: boolean;
  memory?: boolean;
  logic?: boolean;
}

export const QWaveBeam: React.FC<BeamProps> = ({
  source,
  target,
  path,
  prediction = false,
  collapseState,
  sqiScore = 0,
  show = true,
  emotion = false,
  memory = false,
  logic = false,
}) => {
  // loosen refs to avoid @types/three vs three mismatch
  const materialRef = useRef<any>(null);
  const beamRef = useRef<any>(null);
  const pulseRef = useRef(0);

  if (!show) return null;

  // 🎯 compute points along the beam
  const points = useMemo(() => {
    if (path && path.length >= 2) {
      return path.map((p) => new THREE.Vector3(...p));
    }

    const curve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(...source),
      new THREE.Vector3(
        (source[0] + target[0]) / 2,
        (source[1] + target[1]) / 2 + 1.5,
        (source[2] + target[2]) / 2
      ),
      new THREE.Vector3(...target)
    );
    return curve.getPoints(32);
  }, [path, source, target]);

  // 🔺 tube geometry for the beam – cast to any so R3F is happy
  const geometry = useMemo(
    () =>
      (new THREE.TubeGeometry(
        new THREE.CatmullRomCurve3(points),
        32,
        emotion ? 0.12 : memory ? 0.04 : logic ? 0.07 : 0.06,
        8,
        false
      ) as any),
    [points, emotion, memory, logic]
  );

  const getBeamColor = () => {
    if (emotion) return "#FCA5A5";
    if (memory) return "#93C5FD";
    if (logic) return "#6EE7B7";
    if (collapseState === "contradicted") return "#ff3333";
    if (collapseState === "collapsed") return "#00ffee";
    if (prediction) return "#FACC15";
    return "#aaaaff";
  };

  useFrame(() => {
    pulseRef.current += 0.02;
    const oscillation = 0.5 + 0.5 * Math.sin(pulseRef.current);

    if (materialRef.current) {
      materialRef.current.emissiveIntensity = 0.6 + oscillation * sqiScore * 2;
      materialRef.current.opacity = 0.7 + 0.3 * oscillation;
    }
  });

  return (
    <mesh ref={beamRef} geometry={geometry as any}>
      <meshStandardMaterial
        ref={materialRef}
        color={getBeamColor()}
        emissive={getBeamColor()}
        transparent
        opacity={0.9}
        emissiveIntensity={1}
      />
    </mesh>
  );
};

export default QWaveBeam;