"use client";

import React, { useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Text, Float } from "@react-three/drei";
import * as THREE from "three";

// --- O-Series Logic & Pinned Metrics ---
const MODES = {
  O2_EQUILIBRIUM: {
    id: 0, label: "O2: Equilibrium", fidelity: 0.911, mi: 0.671, 
    drift: 8.096e-05, entropyRate: 0.0, status: "STABLE", color: "#4ade80"
  },
  O3_OVERCOUPLED: {
    id: 1, label: "O3: Overcoupled", fidelity: 0.880, mi: 0.750, 
    drift: -1.518e-04, entropyRate: -3.318e-05, status: "OSCILLATORY", color: "#facc15"
  },
  O4_UNLOCKED: {
    id: 2, label: "O4: Unlocked", fidelity: 0.847, mi: 0.997, 
    drift: 0.005, entropyRate: 1.2e-3, status: "DECOHERENT", color: "#f87171"
  },
  O4A_SERVO: {
    id: 3, label: "O4a: Phase Servo", fidelity: 0.922, mi: 0.997, 
    drift: 1e-6, entropyRate: 0.0, status: "METASTABLE", color: "#38bdf8"
  },
  O8_PREDICT: {
    id: 4, label: "O8: Predict Horizon", fidelity: 0.911, mi: 0.671, 
    drift: 1.065e-03, entropyRate: 0.0, status: "PREDICTIVE", color: "#c084fc", corr: 0.999
  },
  O10_DIVERGENT: {
    id: 5, label: "O10: Divergent Loop", fidelity: 0.720, mi: 0.450, 
    drift: -2.66e-04, entropyRate: 1.183e-02, status: "DIVERGENT", color: "#ef4444", corr: 0.980
  }
};

// --- Shaders ---
const ObserverShader = {
  uniforms: {
    uTime: { value: 0 },
    uMode: { value: 0 },
    uIsObserver: { value: 0.0 }, // 0 for System, 1 for Observer
    uFidelity: { value: 0.911 },
    uDrift: { value: 8.096e-05 },
  },
  vertexShader: `
    varying vec2 vUv;
    varying float vWave;
    uniform float uTime;
    uniform float uIsObserver;
    uniform float uDrift;
    uniform float uMode;

    void main() {
      vUv = uv;
      vec3 pos = position;
      
      // System Wave
      float sysWave = sin(pos.x * 0.5 + uTime * 2.0) * cos(pos.y * 0.5 + uTime * 1.5);
      
      // Observer Wave (Delayed or Divergent based on mode)
      float phaseShift = uIsObserver * (0.5 + uDrift * 100.0);
      if (uMode == 5.0) phaseShift += sin(uTime * 5.0) * 0.5; // Divergent desync
      
      float obsWave = sin(pos.x * 0.5 + uTime * 2.0 - phaseShift) * cos(pos.y * 0.5 + uTime * 1.5);
      
      float finalWave = mix(sysWave, obsWave, uIsObserver);
      pos.z += finalWave * 1.5;
      vWave = finalWave;
      
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    varying vec2 vUv;
    varying float vWave;
    uniform float uIsObserver;
    uniform float uMode;

    void main() {
      vec3 sysColor = vec3(0.1, 0.4, 0.9);
      vec3 obsColor = vec3(0.6, 0.2, 0.9);
      
      vec3 color = mix(sysColor, obsColor, uIsObserver);
      float alpha = mix(0.8, 0.5, uIsObserver);
      
      if (uMode == 4.0 && uIsObserver == 0.0) {
        // Add Prediction Ghost (O8)
        float ghost = sin(vUv.x * 50.0 + uIsObserver) * 0.1;
        color += vec3(0.5, 0.5, 1.0) * ghost;
      }

      gl_FragColor = vec4(color * (vWave + 1.2), alpha);
    }
  `
};

// --- Main Component ---
const FieldPlane = ({ isObserver, modeData, time }: { isObserver: boolean, modeData: any, time: number }) => {
  const meshRef = useRef<THREE.Mesh>(null!);
  const uniforms = useMemo(() => THREE.UniformsUtils.clone(ObserverShader.uniforms), []);

  useFrame(() => {
    uniforms.uTime.value = time;
    uniforms.uMode.value = modeData.id;
    uniforms.uIsObserver.value = isObserver ? 1.0 : 0.0;
    uniforms.uFidelity.value = modeData.fidelity;
    uniforms.uDrift.value = modeData.drift;
  });

  return (
    <mesh ref={meshRef} position={[0, isObserver ? 4 : -4, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[20, 20, 64, 64]} />
      <shaderMaterial {...ObserverShader} uniforms={uniforms} transparent side={THREE.DoubleSide} />
    </mesh>
  );
};

const CouplingTendrils = ({ modeData, time }: { modeData: any, time: number }) => {
  const count = 8;
  const points = useMemo(() => {
    const pts = [];
    for (let i = 0; i < count; i++) {
      pts.push(new THREE.Vector3((i - count / 2) * 3, -4, 0));
    }
    return pts;
  }, []);

  return (
    <group>
      {points.map((p, i) => (
        <mesh key={i} position={[p.x, 0, 0]}>
          <cylinderGeometry args={[0.05, 0.05, 8, 8]} />
          <meshBasicMaterial 
            color={modeData.color} 
            transparent 
            opacity={modeData.mi * 0.5 * (0.5 + 0.5 * Math.sin(time * 5.0 + i))} 
          />
        </mesh>
      ))}
    </group>
  );
};

export default function QFCObserverDashboardO() {
  const [mode, setMode] = useState<keyof typeof MODES>("O2_EQUILIBRIUM");
  const [time, setTime] = useState(0);
  const current = MODES[mode];

  // Manual time track for shared uniforms
  React.useEffect(() => {
    let frame = requestAnimationFrame(function loop(t) {
      setTime(t / 1000);
      frame = requestAnimationFrame(loop);
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <div className="flex w-full h-screen bg-[#05050a] text-slate-200 font-mono">
      {/* LEFT: Dual Field Viewport */}
      <div className="w-2/3 h-full relative border-r border-slate-800">
        <Canvas camera={{ position: [15, 10, 15], fov: 45 }}>
          <color attach="background" args={["#05050a"]} />
          <OrbitControls />
          <ambientLight intensity={0.5} />
          
          <FieldPlane isObserver={false} modeData={current} time={time} />
          <FieldPlane isObserver={true} modeData={current} time={time} />
          <CouplingTendrils modeData={current} time={time} />

          {/* Labels in 3D Space */}
          <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
            <Text position={[0, -6, 10]} fontSize={0.8} color="#3b82f6">Ψ_SYSTEM</Text>
            <Text position={[0, 6, 10]} fontSize={0.8} color="#a855f7">Ψ_OBSERVER</Text>
          </Float>
        </Canvas>

        {/* Overlay Mode Selectors */}
        <div className="absolute bottom-8 left-8 flex gap-2 z-10">
          {(Object.keys(MODES) as Array<keyof typeof MODES>).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1 text-[10px] border transition-colors ${
                mode === m ? "bg-slate-200 text-black border-white" : "border-slate-700 hover:border-slate-500"
              }`}
            >
              {MODES[m].label.split(":")[0]}
            </button>
          ))}
        </div>
      </div>

      {/* RIGHT: HUD */}
      <div className="w-1/3 p-8 flex flex-col gap-8 bg-black/50 backdrop-blur-md">
        <header className="border-b border-slate-800 pb-4">
          <h1 className="text-xl font-bold text-white tracking-tighter">O-SERIES_OBSERVER_HUD</h1>
          <p className="text-[10px] text-slate-500 mt-1">LOCKED_RUN: 20251230T232442Z_O</p>
        </header>

        <section className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 border border-slate-800 bg-slate-900/30">
              <p className="text-[9px] text-slate-500 uppercase">Mutual Information</p>
              <p className="text-2xl font-light text-cyan-400">{current.mi.toFixed(3)}</p>
            </div>
            <div className="p-4 border border-slate-800 bg-slate-900/30">
              <p className="text-[9px] text-slate-500 uppercase">Fidelity (F)</p>
              <p className="text-2xl font-light text-purple-400">{current.fidelity.toFixed(3)}</p>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-[10px]">
              <span>SYSTEM_STATUS</span>
              <span style={{ color: current.color }}>{current.status}</span>
            </div>
            <div className="w-full h-1 bg-slate-800">
              <div 
                className="h-full transition-all duration-500" 
                style={{ width: `${current.fidelity * 100}%`, backgroundColor: current.color }}
              />
            </div>
          </div>

          <div className="p-4 border border-slate-800 bg-black/40 text-[11px] space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-500">⟨dS/dt⟩ (Entropy Flow)</span>
              <span>{current.drift.toExponential(3)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Causal Convergence (CI)</span>
              <span className="text-emerald-500">0.029</span>
            </div>
            {current.corr && (
              <div className="flex justify-between">
                <span className="text-slate-500">Prediction Correlation</span>
                <span className="text-fuchsia-400">{current.corr}</span>
              </div>
            )}
          </div>
        </section>

        <footer className="mt-auto pt-8 border-t border-slate-800">
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full animate-pulse`} style={{ backgroundColor: current.color }} />
            <span className="text-[10px] text-slate-500 tracking-widest uppercase">
              {current.label} Target Locked
            </span>
          </div>
        </footer>
      </div>
    </div>
  );
}