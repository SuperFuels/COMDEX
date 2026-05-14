"use client";

import React, { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Float, Text } from "@react-three/drei";
import * as THREE from "three";

export type PSeriesModeKey =
  | "P6_CHAOS"
  | "P7I_ROBUST"
  | "P10M_CERTIFIED"
  | "P10T_STABILITY";

export type PSeriesMode = {
  id: number;
  label: string;
  rValue: number;
  noise: number;
  status: string;
  color: string;
  // always present (fixes your TS union errors)
  description: string;

  // optional stability extras
  gainMargin?: number;
  phaseMargin?: number;
  tauM?: number;
};

// --- P-Series Pinned Metrics (Run: P20251231T183451Z_P) ---
export const P_MODES: Record<PSeriesModeKey, PSeriesMode> = {
  P6_CHAOS: {
    id: 0,
    label: "P6: Non-Lock",
    rValue: 0.12,
    noise: 36.988,
    status: "CHAOTIC",
    color: "#ef4444",
    description: "No global phase lock. High jitter.",
  },
  P7I_ROBUST: {
    id: 1,
    label: "P7i: Attractor",
    rValue: 0.95,
    noise: 0.0035,
    status: "SNAP_LOCK",
    color: "#facc15",
    description: "Attractor snap. Relock time = 0 steps.",
  },
  P10M_CERTIFIED: {
    id: 2,
    label: "P10m: Certified",
    rValue: 0.9989,
    noise: 0.003,
    status: "CERTIFIED",
    color: "#38bdf8",
    description: "100% Pass rate. Global coherence achieved.",
  },
  P10T_STABILITY: {
    id: 3,
    label: "P10t: Stability",
    rValue: 0.9999,
    noise: 0.001,
    status: "STABLE_MARGINS",
    color: "#4ade80",
    description: "Stability margins verified under certified coherence.",
    gainMargin: 2392.13,
    phaseMargin: 179.8,
    tauM: 0.287,
  },
};

// --- Resonance Lattice Shader (retain the real math) ---
const ResonanceShader = {
  uniforms: {
    uTime: { value: 0 },
    uRValue: { value: 0.12 },
    uNoise: { value: 36.988 },
    uColor: { value: new THREE.Color("#ef4444") },
  },
  vertexShader: `
    varying vec2 vUv;
    varying float vDistance;
    uniform float uTime;
    uniform float uRValue;
    uniform float uNoise;

    void main() {
      vUv = uv;
      vec3 pos = position;

      // Calculate jitter based on inverse of R-value and noise metric
      float jitterStrength = (1.0 - uRValue) * (uNoise * 0.05);
      float noise = sin(pos.x * 10.0 + uTime * 5.0) * cos(pos.y * 10.0 + uTime * 5.0);

      // Apply chaotic jitter or resonant pulse
      pos.z += noise * jitterStrength;

      // Global resonant pulse (Phase C/D)
      float pulse = sin(uTime * 2.94) * 0.2 * uRValue; // 2.94 rad/s ~ f_peak
      pos.z += pulse;

      vDistance = pos.z;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    varying vec2 vUv;
    varying float vDistance;
    uniform vec3 uColor;
    uniform float uRValue;

    void main() {
      float grid = sin(vUv.x * 100.0) * sin(vUv.y * 100.0);
      vec3 finalColor = mix(vec3(0.1), uColor, step(0.9, grid));

      // Bloom-ish add based on coherence (R-Value)
      float glow = vDistance * uRValue;
      gl_FragColor = vec4(finalColor + glow, 0.8);
    }
  `,
};

function coercePModeKey(x: any): PSeriesModeKey | null {
  if (x === "P6_CHAOS") return x;
  if (x === "P7I_ROBUST") return x;
  if (x === "P10M_CERTIFIED") return x;
  if (x === "P10T_STABILITY") return x;
  return null;
}

function ResonantField({ modeData }: { modeData: PSeriesMode }) {
  const uniforms = useMemo(
    () => THREE.UniformsUtils.clone(ResonanceShader.uniforms),
    [],
  );
  const tRef = useRef(0);

  useFrame((_, dtRaw) => {
    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;

    uniforms.uTime.value = tRef.current;
    uniforms.uRValue.value = modeData.rValue;
    uniforms.uNoise.value = modeData.noise;
    uniforms.uColor.value.set(modeData.color);
  });

  return (
    <mesh rotation={[-Math.PI / 2.5, 0, 0]} position={[0, -2, 0]}>
      <planeGeometry args={[25, 25, 128, 128]} />
      <shaderMaterial
        uniforms={uniforms}
        vertexShader={ResonanceShader.vertexShader}
        fragmentShader={ResonanceShader.fragmentShader}
        transparent
        wireframe={modeData.rValue < 0.5}
      />
    </mesh>
  );
}

type Props = {
  frame?: any; // keep loose; selection is usually routed through viewport state
};

export default function QFCDemoPSeries({ frame }: Props) {
  // allow external selection (dropdown) but keep a sane default
  const key =
    coercePModeKey(frame?.pMode) ??
    coercePModeKey(frame?.p_mode) ??
    coercePModeKey(frame?.pSeries) ??
    coercePModeKey(frame?.mode) ??
    "P6_CHAOS";

  const current = P_MODES[key];

  return (
    <group>
      <ResonantField modeData={current} />

      {/* in-canvas status marker (no DOM; compatible with shared Canvas) */}
      <Float
        speed={Math.max(0.1, current.rValue * 5)}
        rotationIntensity={0.2}
        floatIntensity={0.5}
      >
        <Text
          position={[0, 3.2, -4]}
          fontSize={0.8}
          color={current.color}
          anchorX="center"
          anchorY="middle"
        >
          {current.status}
        </Text>

        <Text
          position={[0, 2.35, -4]}
          fontSize={0.28}
          color={"#cbd5e1"}
          anchorX="center"
          anchorY="middle"
        >
          {current.label}  ·  R={current.rValue.toFixed(4)}  ·  noise={current.noise.toFixed(4)}
        </Text>

        {(current.gainMargin != null || current.phaseMargin != null || current.tauM != null) && (
          <Text
            position={[0, 1.9, -4]}
            fontSize={0.24}
            color={"#94a3b8"}
            anchorX="center"
            anchorY="middle"
          >
            {`GM=${current.gainMargin ?? "—"}  PM=${current.phaseMargin ?? "—"}°  τm=${current.tauM ?? "—"}`}
          </Text>
        )}
      </Float>
    </group>
  );
}