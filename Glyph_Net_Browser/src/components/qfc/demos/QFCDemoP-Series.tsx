"use client";

import React, { useMemo, useRef, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Text, Float, MeshDistortMaterial, Points, PointMaterial } from "@react-three/drei";
import * as THREE from "three";

// --- P-Series Pinned Metrics (Run: P20251231T183451Z_P) ---
const P_MODES = {
  P6_CHAOS: {
    id: 0, label: "P6: Non-Lock", rValue: 0.12, noise: 36.988, 
    status: "CHAOTIC", color: "#ef4444", description: "No global phase lock. High jitter."
  },
  P7I_ROBUST: {
    id: 1, label: "P7i: Attractor", rValue: 0.95, noise: 0.0035, 
    status: "SNAP_LOCK", color: "#facc15", description: "Attractor snap. Relock time = 0 steps."
  },
  P10M_CERTIFIED: {
    id: 2, label: "P10m: Certified", rValue: 0.9989, noise: 0.003, 
    status: "CERTIFIED", color: "#38bdf8", description: "100% Pass rate. Global coherence achieved."
  },
  P10T_STABILITY: {
    id: 3, label: "P10t: Stability", rValue: 0.9999, noise: 0.001, 
    status: "STABLE_MARGINS", color: "#4ade80", 
    gainMargin: 2392.13, phaseMargin: 179.8, tauM: 0.287
  }
};

// --- Resonance Lattice Shader ---
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
      
      // Bloom effect based on coherence (R-Value)
      float glow = vDistance * uRValue;
      gl_FragColor = vec4(finalColor + glow, 0.8);
    }
  `
};

const ResonantField = ({ modeData, time }: { modeData: any, time: number }) => {
  const meshRef = useRef<THREE.Mesh>(null!);
  const uniforms = useMemo(() => THREE.UniformsUtils.clone(ResonanceShader.uniforms), []);

  useFrame(() => {
    uniforms.uTime.value = time;
    uniforms.uRValue.value = modeData.rValue;
    uniforms.uNoise.value = modeData.noise;
    uniforms.uColor.value.set(modeData.color);
  });

  return (
    <mesh ref={meshRef} rotation={[-Math.PI / 2.5, 0, 0]} position={[0, -2, 0]}>
      <planeGeometry args={[25, 25, 128, 128]} />
      <shaderMaterial {...ResonanceShader} uniforms={uniforms} transparent wireframe={modeData.rValue < 0.5} />
    </mesh>
  );
};

export default function PSeriesResonanceDashboard() {
  const [mode, setMode] = useState<keyof typeof P_MODES>("P6_CHAOS");
  const [time, setTime] = useState(0);
  const current = P_MODES[mode];

  useEffect(() => {
    let frame = requestAnimationFrame(function loop(t) {
      setTime(t / 1000);
      frame = requestAnimationFrame(loop);
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <div className="flex w-full h-screen bg-[#020205] text-slate-300 font-mono overflow-hidden">
      {/* 3D VIEWPORT */}
      <div className="w-2/3 h-full relative">
        <Canvas camera={{ position: [0, 5, 18], fov: 40 }}>
          <color attach="background" args={["#020205"]} />
          <OrbitControls maxPolarAngle={Math.PI / 2} />
          <ambientLight intensity={0.2} />
          <pointLight position={[10, 10, 10]} intensity={1.5} color={current.color} />
          
          <ResonantField modeData={current} time={time} />

          <Float speed={current.rValue * 5} rotationIntensity={0.2} floatIntensity={0.5}>
            <Text position={[0, 8, -5]} fontSize={1.2} color={current.color} font="/fonts/Inter-Bold.woff">
              {current.status}
            </Text>
          </Float>
        </Canvas>

        {/* MODE SELECTOR */}
        <div className="absolute bottom-10 left-10 flex gap-3">
          {(Object.keys(P_MODES) as Array<keyof typeof P_MODES>).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-4 py-2 text-xs border uppercase tracking-widest transition-all ${
                mode === m ? "bg-white text-black border-white" : "border-slate-800 hover:border-slate-400"
              }`}
            >
              {P_MODES[m].label}
            </button>
          ))}
        </div>
      </div>

      {/* HUD PANEL */}
      <div className="w-1/3 p-10 bg-black/80 backdrop-blur-xl border-l border-white/5 flex flex-col">
        <header className="mb-10">
          <h1 className="text-2xl font-black tracking-tighter text-white">P-SERIES_RESONANCE</h1>
          <p className="text-[10px] text-slate-500">RUN_ID: P20251231T183451Z_P</p>
        </header>

        <div className="space-y-8 flex-1">
          {/* COHERENCE METER */}
          <section>
            <div className="flex justify-between text-[10px] mb-2">
              <span>GLOBAL_ORDER_PARAMETER (R)</span>
              <span className="text-white">{current.rValue.toFixed(4)}</span>
            </div>
            <div className="w-full h-1.5 bg-white/10">
              <div 
                className="h-full transition-all duration-1000 ease-out"
                style={{ width: `${current.rValue * 100}%`, backgroundColor: current.color }}
              />
            </div>
          </section>

          {/* STABILITY STATS */}
          <div className="grid grid-cols-1 gap-4">
            <div className="p-4 border border-white/5 bg-white/[0.02]">
              <p className="text-[9px] text-slate-500 uppercase mb-1">Resonance Verdict</p>
              <p className="text-lg font-light" style={{ color: current.color }}>{current.description}</p>
            </div>
            
            {current.gainMargin && (
              <div className="grid grid-cols-2 gap-4 animate-in fade-in slide-in-from-right-4 duration-500">
                <div className="p-4 border border-white/5 bg-white/[0.02]">
                  <p className="text-[9px] text-slate-500 uppercase">Gain Margin</p>
                  <p className="text-xl text-emerald-400">{current.gainMargin}</p>
                </div>
                <div className="p-4 border border-white/5 bg-white/[0.02]">
                  <p className="text-[9px] text-slate-500 uppercase">Phase Margin</p>
                  <p className="text-xl text-emerald-400">{current.phaseMargin}°</p>
                </div>
              </div>
            )}
          </div>

          {/* DYNAMIC LOGS */}
          <div className="p-4 border border-white/5 bg-black text-[10px] font-mono leading-relaxed h-48 overflow-hidden text-slate-500">
            <div className="animate-pulse text-white mb-2 underline">SYSTEM_LOG_STREAM</div>
            <p>&gt; Initializing Lattice... OK</p>
            <p>&gt; Noise Floor: {current.noise.toFixed(3)}</p>
            <p>&gt; Phase Difference: {(1 - current.rValue).toExponential(3)}</p>
            {current.tauM && <p>&gt; Memory Kernel (τm): {current.tauM}s</p>}
            <p className="text-slate-700">&gt; Kernel Spectral Peak: 0.4688 Hz</p>
            <p className="text-slate-700">&gt; Q-Factor: 0.75 (Stable Damping)</p>
          </div>
        </div>

        <footer className="mt-auto pt-6 border-t border-white/5">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: current.color }} />
            <span className="text-[9px] tracking-[0.2em] text-white">RESONANT_LOCK_CERTIFIED</span>
          </div>
        </footer>
      </div>
    </div>
  );
}