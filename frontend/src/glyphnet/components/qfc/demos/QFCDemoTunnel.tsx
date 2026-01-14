"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const n = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

export default function QFCDemoTunnel({ frame }: { frame: any }) {
  const meshRef = useRef<THREE.Points>(null);

  // ✅ stable time accumulator (FPS-drop safe)
  const tRef = useRef(0);

  // ✅ smooth topology gate (prevents “epoch stepping” jitter)
  const gateSm = useRef(1.0);

  // Causal Constants
  const BARRIER_Z = -5.0;
  const BARRIER_WIDTH_BASE = 2.5;

  const { basePoints, positions, colors } = useMemo(() => {
    const COUNT = 4500; // density
    const base = new Float32Array(COUNT * 3);
    const pos = new Float32Array(COUNT * 3);
    const col = new Float32Array(COUNT * 3);

    for (let i = 0; i < COUNT; i++) {
      base[i * 3 + 0] = (Math.random() - 0.5) * 4.5;
      base[i * 3 + 1] = (Math.random() - 0.5) * 4.5;
      base[i * 3 + 2] = (Math.random() - 0.5) * 36 - 18;

      pos[i * 3 + 0] = base[i * 3 + 0];
      pos[i * 3 + 1] = base[i * 3 + 1];
      pos[i * 3 + 2] = base[i * 3 + 2];

      col[i * 3 + 0] = 1;
      col[i * 3 + 1] = 1;
      col[i * 3 + 2] = 1;
    }

    return { basePoints: base, positions: pos, colors: col };
  }, []);

  useFrame((_state, dtRaw) => {
    const pts = meshRef.current;
    if (!pts) return;

    // ✅ dt clamp pattern (use everywhere)
    const dtc = Math.min(dtRaw, 1 / 30);

    // ✅ stable time (instead of clock.getElapsedTime)
    tRef.current += dtc;
    const t = tRef.current * 2.5; // keep original feel (scaled)

    // canonical scalars
    const sigma = clamp01(n(frame?.sigma, 0.5));
    const alpha = clamp01(n(frame?.alpha, 0.2));

    // ✅ topology gate plumbing (prefers injected topo_gate01, then topology.gate, then sigma)
    const targetGate = clamp01(n(frame?.topo_gate01, n(frame?.topology?.gate, sigma)));

    // ✅ smooth gate (use dtc)
    const gateLerp = 1 - Math.exp(-dtc * 10.0);
    gateSm.current = gateSm.current + (targetGate - gateSm.current) * gateLerp;
    const topoGate01 = gateSm.current;

    // Gate drives “behavior”:
    // - gate high => more transmission, less reflection, slightly faster wavefront
    // - gate low  => more reflection, stronger decay in barrier
    const v = (2.0 + sigma * 4.0) * (0.85 + 0.30 * topoGate01);

    const transmission = clamp01((0.04 + alpha * 0.72) * (0.55 + 0.45 * topoGate01)); // 0..1-ish
    const reflectionScale = (1.0 - transmission) * (0.90 - 0.55 * topoGate01); // gate ↑ => reflection ↓

    const barrierWidth = BARRIER_WIDTH_BASE * (0.92 + 0.18 * topoGate01);
    const barrierHardness = 5.0 - 3.0 * topoGate01; // gate ↑ => barrier “softer”

    const posAttr = pts.geometry.attributes.position.array as Float32Array;
    const colAttr = pts.geometry.attributes.color.array as Float32Array;

    const invLen = 1.0 / 1.5;

    for (let i = 0; i < basePoints.length / 3; i++) {
      const x0 = basePoints[i * 3 + 0];
      const y0 = basePoints[i * 3 + 1];
      const z0 = basePoints[i * 3 + 2];

      // 1) INCIDENT WAVE (moving forward)
      const centerIn = ((t * v) % 44) - 22;
      const dzIn = z0 - centerIn;
      const pulseIn = Math.exp(-(dzIn * dzIn) * invLen);

      // 2) REFLECTED WAVE (from barrier, moving backward)
      const reflectionStart = BARRIER_Z;
      const centerRefl = reflectionStart + ((t * v) % 44);
      const dzRefl = z0 - centerRefl;
      const pulseRefl = Math.exp(-(dzRefl * dzRefl) * invLen) * reflectionScale;

      // 3) BARRIER REGIONS
      const inBarrier = z0 > BARRIER_Z && z0 < BARRIER_Z + barrierWidth;
      const pastBarrier = z0 >= BARRIER_Z + barrierWidth;

      let intensity = 0;
      let r = 1,
        g = 1,
        b = 1;

      if (inBarrier) {
        // Tunneling Decay (Red) — gate ↑ reduces decay (more passes through)
        intensity =
          pulseIn * Math.exp(-(z0 - BARRIER_Z) * (barrierHardness - transmission * 2.0));
        r = 1.0;
        g = 0.1;
        b = 0.1;
      } else if (pastBarrier) {
        // Emerged Wave (Cyan) — gate ↑ increases emerged strength
        intensity = pulseIn * (0.03 + transmission * 0.75);
        r = 0.2;
        g = 0.8;
        b = 1.0;
      } else {
        // Interference Zone (before barrier)
        intensity = pulseIn + pulseRefl * 0.6;

        if (pulseRefl > pulseIn * 0.8) {
          r = 0.6;
          g = 0.2;
          b = 1.0; // reflection tint
        } else {
          r = 1.0;
          g = 0.9;
          b = 0.4; // incident tint
        }
      }

      // “truth wave” modulation — slightly faster when gate is high
      const wSpeed = 15.0 * (0.92 + 0.25 * topoGate01);
      const phase = z0 * 3.0 - t * wSpeed;
      const wave = Math.sin(phase) * intensity * 0.6;

      posAttr[i * 3 + 0] = x0 + wave;
      posAttr[i * 3 + 1] = y0 + Math.cos(phase) * intensity * 0.6;
      posAttr[i * 3 + 2] = z0;

      colAttr[i * 3 + 0] = r;
      colAttr[i * 3 + 1] = g;
      colAttr[i * 3 + 2] = b;
    }

    pts.geometry.attributes.position.needsUpdate = true;
    pts.geometry.attributes.color.needsUpdate = true;
  });

  // optional: make barrier “look” more closed when gate is low
  const topoGateForBarrier = gateSm.current;
  const barrierOpacity = 0.10 + (1 - topoGateForBarrier) * 0.18;

  return (
    <group>
      <points ref={meshRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={positions.length / 3}
            array={positions}
            itemSize={3}
          />
          <bufferAttribute
            attach="attributes-color"
            count={colors.length / 3}
            array={colors}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.07}
          vertexColors
          transparent
          opacity={0.75}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </points>

      {/* The Causal Barrier */}
      <mesh position={[0, 0, BARRIER_Z + BARRIER_WIDTH_BASE / 2]}>
        <boxGeometry args={[6, 6, BARRIER_WIDTH_BASE]} />
        <meshBasicMaterial color="#334155" transparent opacity={barrierOpacity} wireframe />
      </mesh>
    </group>
  );
}