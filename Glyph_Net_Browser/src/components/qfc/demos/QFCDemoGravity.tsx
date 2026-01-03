"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const n = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

export default function QFCDemoGravity({ frame }: { frame: any }) {
  const meshRef = useRef<THREE.Points>(null);
  const coreRef = useRef<THREE.Mesh>(null);

  // ✅ smooth gate so epoch updates don’t look “steppy”
  const gateSm = useRef(1.0);

  // ✅ stable time accumulator (FPS-drop stable)
  const tRef = useRef(0);

  // High-density lattice for metric distortion
  const { points, count } = useMemo(() => {
    const size = 20;
    const res = 80;
    const p = new Float32Array(res * res * 3);

    for (let i = 0; i < res; i++) {
      for (let j = 0; j < res; j++) {
        const x = (i / res - 0.5) * size;
        const z = (j / res - 0.5) * size;
        const k = (i * res + j) * 3;
        p[k + 0] = x;
        p[k + 1] = 0;
        p[k + 2] = z;
      }
    }

    return { points: p, count: res * res };
  }, []);

  useFrame((_state, dtRaw) => {
    if (!meshRef.current || !coreRef.current) return;

    // ✅ dt clamp pattern (use in every useFrame)
    const dtc = Math.min(dtRaw, 1 / 30);

    // ✅ stable time accumulator
    tRef.current += dtc;
    const t = tRef.current;

    // Telemetry Mapping (clamped)
    const kappa = clamp01(n(frame?.kappa, 0.25));
    const curv = n(frame?.curv, 0.18);
    const alpha = clamp01(n(frame?.alpha, 0.12));

    // ✅ Topology gate plumbing (prefers injected topo_gate01, then topology.gate, then sigma)
    const targetGate = clamp01(n(frame?.topo_gate01, n(frame?.topology?.gate, n(frame?.sigma, 1))));

    // ✅ smooth gate (use dtc)
    const gateLerp = 1 - Math.exp(-dtc * 10.0);
    gateSm.current = gateSm.current + (targetGate - gateSm.current) * gateLerp;
    const topoGate01 = gateSm.current;

    const geom = meshRef.current.geometry;
    const attr = geom.attributes.position;
    if (!attr) return;

    const posAttr = attr.array as Float32Array;

    // Gate-driven behavior
    const depthGain = 0.75 + 0.85 * topoGate01; // 0.75..1.60
    const tightGain = 0.8 + 0.7 * topoGate01; // 0.80..1.50
    const waveGain = 0.6 + 0.55 * (1 - topoGate01); // more waves when gate low

    // Core dynamics: “Pulsing Singularity”
    const pulseRate = 1.4 + alpha * 2.2;
    const pulseAmp = 0.12 * (0.65 + 0.35 * (1 - topoGate01));
    const pulse = 1.0 + pulseAmp * Math.sin(t * pulseRate);

    coreRef.current.scale.setScalar(
      pulse * (0.75 + Math.max(0, curv) * 1.6) * (0.85 + 0.25 * topoGate01),
    );
    coreRef.current.rotation.y = t * (0.45 + 0.25 * topoGate01);

    // Metric Displacement (Lorentzian-ish well)
    const depthBase = (Math.max(0, curv) * 6.0 + kappa * 2.0) * depthGain;
    const tightBase = (1.0 + kappa * 4.0) * tightGain;

    for (let i = 0; i < count; i++) {
      const k = i * 3;
      const px = posAttr[k + 0];
      const pz = posAttr[k + 2];
      const dist = Math.sqrt(px * px + pz * pz);

      const displacement = -(depthBase / (1.0 + Math.pow(dist / tightBase, 2.0)));

      // Background waves: stronger when gate is low
      const waves = Math.sin(dist * 1.2 - t * 2.5) * 0.08 * alpha * waveGain;

      posAttr[k + 1] = displacement + waves;
    }

    attr.needsUpdate = true;
  });

  return (
    <group position={[0, 1.5, 0]}>
      {/* Central Mass (Causal Core) */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[1, 64, 64]} />
        <meshStandardMaterial
          color={"#0ea5e9"}
          emissive={"#38bdf8"}
          emissiveIntensity={2.0}
          roughness={0.1}
          metalness={0.9}
        />
        <pointLight intensity={2.5} distance={15} color="#38bdf8" />
      </mesh>

      {/* Warped Spacetime Lattice */}
      <points ref={meshRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" count={points.length / 3} array={points} itemSize={3} />
        </bufferGeometry>
        <pointsMaterial
          size={0.06}
          color="#94a3b8"
          transparent
          opacity={0.4}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </points>

      {/* Event Horizon Glow */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]}>
        <ringGeometry args={[0.5, 6, 64]} />
        <meshBasicMaterial color="#0ea5e9" transparent opacity={0.05} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}