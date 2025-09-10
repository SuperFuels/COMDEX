import * as THREE from "three";
import React, { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";

export interface BeamProps {
  source: [number, number, number];
  target: [number, number, number];
  path?: [number, number, number][]; // ✅ Added
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
  const materialRef = useRef<THREE.MeshStandardMaterial>(null);
  const beamRef = useRef<THREE.Mesh>(null);
  const pulse = useRef(0);

  if (!show) return null;

  // 🎯 Compute points
  const points = useMemo(() => {
    if (path && path.length >= 2) {
      return path.map((p) => new THREE.Vector3(...p));
    }

    // default to quadratic curve
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

  const geometry = useMemo(() => {
    return new THREE.TubeGeometry(
      new THREE.CatmullRomCurve3(points),
      32,
      emotion ? 0.12 : memory ? 0.04 : logic ? 0.07 : 0.06,
      8,
      false
    );
  }, [points, emotion, memory, logic]);

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
    pulse.current += 0.02;
    const oscillation = 0.5 + 0.5 * Math.sin(pulse.current);
    if (materialRef.current) {
      materialRef.current.emissiveIntensity = 0.6 + oscillation * sqiScore * 2;
      materialRef.current.opacity = 0.7 + 0.3 * oscillation;
    }
  });

  return (
    <mesh geometry={geometry} ref={beamRef}>
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