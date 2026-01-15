"use client";

import React, { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html, Text, Float, OrbitControls } from "@react-three/drei";
import * as THREE from "three";

// Workaround: Drei/R3F typing mismatches in some Next builds.
// Runtime is identical; this only unblocks Next typecheck.
const DreiText: any = Text;
const DreiFloat: any = Float;
const DreiOrbitControls: any = OrbitControls;

/**
 * O-Series Observer Dashboard (typecheck-safe for Next build)
 */

// --- O-Series Mode Data (Retained) ---
const MODES = {
  O2_EQUILIBRIUM: {
    id: 0,
    label: "O2: Equilibrium",
    fidelity: 0.911,
    mi: 0.671,
    drift: 8.096e-5,
    status: "STABLE",
    color: "#00f2ff",
  },
  O3_OVERCOUPLED: {
    id: 1,
    label: "O3: Overcoupled",
    fidelity: 0.88,
    mi: 0.75,
    drift: -1.518e-4,
    status: "OSCILLATORY",
    color: "#facc15",
  },
  O4_UNLOCKED: {
    id: 2,
    label: "O4: Unlocked",
    fidelity: 0.847,
    mi: 0.997,
    drift: 0.005,
    status: "DECOHERENT",
    color: "#f87171",
  },
  O4A_SERVO: {
    id: 3,
    label: "O4a: Phase Servo",
    fidelity: 0.922,
    mi: 0.997,
    drift: 1e-6,
    status: "METASTABLE",
    color: "#38bdf8",
  },
  O8_PREDICT: {
    id: 4,
    label: "O8: Predict Horizon",
    fidelity: 0.911,
    mi: 0.671,
    drift: 1.065e-3,
    status: "PREDICTIVE",
    color: "#c084fc",
    corr: 0.999,
  },
  O10_DIVERGENT: {
    id: 5,
    label: "O10: Divergent Loop",
    fidelity: 0.72,
    mi: 0.45,
    drift: -2.66e-4,
    status: "DIVERGENT",
    color: "#ef4444",
    corr: 0.98,
  },
} as const;

type ModeKey = keyof typeof MODES;

const ObserverShader = {
  uniforms: {
    uTime: { value: 0 },
    uIsObserver: { value: 0.0 },
    uFidelity: { value: 0.911 },
    uDrift: { value: 0.0 },
    uColor: { value: new THREE.Color("#00f2ff") },
  },
  vertexShader: `
    varying vec2 vUv;
    varying float vWave;
    uniform float uTime;
    uniform float uIsObserver;
    uniform float uDrift;

    void main() {
      vUv = uv;
      vec3 pos = position;

      // Base Waveform
      float wave = sin(pos.x * 0.3 + uTime * 1.5) * cos(pos.y * 0.3 + uTime * 1.2);

      // Observer Drift (Phase Desync)
      float phase = uIsObserver * (uDrift * 50.0 + sin(uTime * 0.5) * 0.2);
      float finalWave = sin(pos.x * 0.3 + uTime * 1.5 - phase) * cos(pos.y * 0.3 + uTime * 1.2);

      pos.z += finalWave * 2.0;
      vWave = finalWave;

      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
      gl_PointSize = (uIsObserver > 0.5) ? 2.5 : 2.0;
    }
  `,
  fragmentShader: `
    varying float vWave;
    uniform float uIsObserver;
    uniform vec3 uColor;

    void main() {
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      vec3 sysCol = vec3(0.0, 0.8, 1.0); // Cyan
      vec3 obsCol = vec3(0.5, 0.2, 1.0); // Violet

      vec3 base = mix(sysCol, obsCol, uIsObserver);

      // Mode-specific color tint
      base = mix(base, uColor, 0.4);

      float glow = pow(vWave + 1.0, 2.0) * 0.5;
      gl_FragColor = vec4(base * (0.6 + glow), 0.7);
    }
  `,
};

function VolumetricField({
  isObserver,
  modeData,
  time,
}: {
  isObserver: boolean;
  modeData: (typeof MODES)[ModeKey];
  time: number;
}) {
  const uniforms = useMemo(
    () => THREE.UniformsUtils.clone(ObserverShader.uniforms),
    [],
  );

  // Static geometry instance
  const geo = useMemo(() => new THREE.PlaneGeometry(24, 24, 80, 80), []);

  useFrame(() => {
    uniforms.uTime.value = time;
    uniforms.uIsObserver.value = isObserver ? 1.0 : 0.0;
    uniforms.uDrift.value = modeData.drift;
    uniforms.uColor.value.set(modeData.color);
    uniforms.uFidelity.value = modeData.fidelity;
  });

  return (
    <points
      position={[0, isObserver ? 4 : -4, 0]}
      rotation={[-Math.PI / 2, 0, 0]}
    >
      <primitive object={geo} attach="geometry" />
      <shaderMaterial
        uniforms={uniforms}
        vertexShader={ObserverShader.vertexShader}
        fragmentShader={ObserverShader.fragmentShader}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

function CouplingLattice({
  modeData,
  time,
}: {
  modeData: (typeof MODES)[ModeKey];
  time: number;
}) {
  const count = 12;
  const positions = useMemo(
    () => Array.from({ length: count }, (_, i) => (i - count / 2) * 2.5),
    [],
  );

  return (
    <group>
      {positions.map((x, i) => (
        <mesh key={i} position={[x, 0, Math.sin(time + x) * 2]}>
          <cylinderGeometry args={[0.02, 0.02, 8, 8]} />
          <meshBasicMaterial
            color={modeData.color}
            transparent
            opacity={modeData.mi * 0.4 * (0.5 + 0.5 * Math.sin(time * 3 + i))}
          />
        </mesh>
      ))}
    </group>
  );
}

export default function QFCObserverDashboardO({ frame }: { frame?: any }) {
  const [mode, setMode] = useState<ModeKey>("O2_EQUILIBRIUM");
  const current = MODES[mode];

  // stable time accumulator
  const tRef = useRef(0);

  useFrame((_state, dtRaw) => {
    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;
  });

  return (
    <group>
      <DreiOrbitControls enableDamping dampingFactor={0.05} />

      <VolumetricField isObserver={false} modeData={current} time={tRef.current} />
      <VolumetricField isObserver={true} modeData={current} time={tRef.current} />
      <CouplingLattice modeData={current} time={tRef.current} />

      <DreiFloat speed={1.5} floatIntensity={0.2}>
        <DreiText
          position={[-10, -5, 0]}
          fontSize={0.6}
          color="#00f2ff"
          rotation={[0, Math.PI / 4, 0]}
        >
          Ψ_SYS
        </DreiText>
        <DreiText
          position={[-10, 5, 0]}
          fontSize={0.6}
          color="#8b5cf6"
          rotation={[0, Math.PI / 4, 0]}
        >
          Ψ_OBS
        </DreiText>
      </DreiFloat>

      <Html fullscreen transform={false}>
        <div className="pointer-events-none w-full h-full font-mono text-slate-200 p-8">
          {/* Top Right HUD Panel */}
          <div className="absolute top-8 right-8 w-80 p-6 bg-black/60 backdrop-blur-xl border border-white/10 rounded-lg pointer-events-auto">
            <h2 className="text-cyan-400 text-xs tracking-[0.3em] font-bold border-b border-white/10 pb-2 mb-4">
              OBSERVER_IDENTITY_V7
            </h2>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span className="text-slate-500 uppercase">
                    Mutual Information
                  </span>
                  <span className="text-white">{current.mi.toFixed(3)} bits</span>
                </div>
                <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-cyan-500 transition-all duration-700"
                    style={{ width: `${current.mi * 100}%` }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div className="bg-white/5 p-2 rounded">
                  <div className="text-slate-500">FIDELITY</div>
                  <div className="text-purple-400 font-bold">
                    {(current.fidelity * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="bg-white/5 p-2 rounded">
                  <div className="text-slate-500">DRIFT</div>
                  <div className="text-red-400 font-bold">
                    {current.drift.toExponential(2)}
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-white/5">
                <div className="flex items-center gap-2">
                  <div
                    className="w-2 h-2 rounded-full animate-pulse"
                    style={{ background: current.color }}
                  />
                  <span
                    className="text-[10px] uppercase tracking-widest"
                    style={{ color: current.color }}
                  >
                    {current.status}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Left Mode Selector */}
          <div className="absolute bottom-8 left-8 flex flex-col gap-1 pointer-events-auto">
            <span className="text-[8px] text-slate-500 mb-2 tracking-[0.4em]">
              SELECT_MODE_O_SERIES
            </span>
            <div className="flex gap-2">
              {(Object.keys(MODES) as ModeKey[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`px-3 py-1 text-[9px] border transition-all ${
                    mode === m
                      ? "bg-white text-black border-white"
                      : "border-white/20 text-slate-400 hover:border-white/50"
                  }`}
                >
                  {m.split("_")[0]}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Html>
    </group>
  );
}