"use client";

import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

// --- N-Series Master Shader: Nonlinear Feedback & Noise ---
const nSeriesShader = {
  uniforms: {
    uTime: { value: 0 },
    uMode: { value: 0 }, // 0: Stable, 1: Noise, 2: Echo, 3: Rephase, 4: Runaway
    uNoiseSigma: { value: 0.0 },
    uFidelity: { value: 1.0 },
    uPhaseShift: { value: 0.0 },
  },
  vertexShader: `
    varying float vIntensity;
    varying vec2 vUv;
    uniform float uTime;
    uniform float uMode;
    uniform float uNoiseSigma;

    // Pseudo-random generator for i.i.d. noise (N6/N7)
    float rand(vec2 co){
      return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
    }

    void main() {
      vUv = uv;
      vec3 pos = position;

      // Base Wave (u field)
      float wave = sin(pos.x * 0.2 + uTime * 3.0) * cos(pos.y * 0.2 + uTime * 2.0);
      
      // Mode 1: Noise Injection (N6/N7)
      if (uMode == 1.0) {
        float noise = (rand(pos.xy + uTime) - 0.5) * uNoiseSigma * 20.0;
        wave += noise;
      }

      // Mode 4: Runaway / Backreaction (N9)
      if (uMode == 4.0) {
        wave *= exp(sin(uTime * 0.5) * 2.0); // Exponential runaway
        pos.z += sin(pos.x * 0.5) * 5.0;     // Curvature collapse visual
      }

      pos.z += wave * 2.0;
      vIntensity = wave;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    varying float vIntensity;
    varying vec2 vUv;
    uniform float uMode;
    uniform float uFidelity;

    void main() {
      vec3 color;
      
      if (uMode == 2.0) { // Echo Recovery (N5) - Split Screen logic
        if (vUv.x < 0.5) {
          color = vec3(0.1, 0.1, 0.1) + (vIntensity * 0.2); // Scrambled/Dark
        } else {
          color = vec3(0.0, 1.0, 0.6) * vIntensity; // Recovered/Coherent
        }
      } else if (uMode == 3.0) { // Thermal Rephase (N15)
        color = mix(vec3(0.8, 0.2, 0.1), vec3(0.1, 0.6, 1.0), uFidelity);
        color *= vIntensity;
      } else {
        color = mix(vec3(0.05, 0.05, 0.1), vec3(0.2, 0.5, 1.0), vIntensity);
      }

      gl_FragColor = vec4(color, 1.0);
    }
  `
};

export default function QFCFeedbackControllerN() {
  const meshRef = useRef<THREE.Mesh>(null);
  const [mode, setMode] = useState("STABLE"); // STABLE, NOISE, ECHO, REPHASE, RUNAWAY
  
  const modes = {
    STABLE: { id: 0, sigma: 0.0, fidelity: 1.0, label: "N20 Unified Equilibrium" },
    NOISE: { id: 1, sigma: 0.0631, fidelity: 0.9, label: "N6 Noise Robustness" },
    ECHO: { id: 2, sigma: 0.0, fidelity: 1.0, label: "N5 Echo Recovery" },
    REPHASE: { id: 3, sigma: 0.0, fidelity: 0.816, label: "N15 Thermal Rephase" },
    RUNAWAY: { id: 4, sigma: 0.5, fidelity: 0.1, label: "N9 Backreaction Runaway" }
  };

  useFrame(({ clock }) => {
    if (meshRef.current) {
      const mat = meshRef.current.material as THREE.ShaderMaterial;
      const current = modes[mode as keyof typeof modes];
      mat.uniforms.uTime.value = clock.getElapsedTime();
      mat.uniforms.uMode.value = current.id;
      mat.uniforms.uNoiseSigma.value = current.sigma;
      mat.uniforms.uFidelity.value = current.fidelity;
    }
  });

  return (
    <div className="w-full h-full bg-[#020205] relative flex flex-col items-center justify-center font-mono text-white overflow-hidden">
      {/* N-SERIES MASTER HUD */}
      <div className="absolute top-6 left-6 z-20 p-5 border border-cyan-900/50 bg-black/90 backdrop-blur-xl w-80 shadow-2xl">
        <div className="flex justify-between items-center border-b border-cyan-900/50 pb-2 mb-4">
          <span className="text-cyan-400 font-bold text-sm tracking-widest">N_CORE_v0.4</span>
          <span className="text-[10px] text-cyan-700">RUN_20251230T224009Z_N</span>
        </div>

        <div className="space-y-3 text-[11px]">
          <div className="flex justify-between">
            <span className="text-gray-500">ACTIVE_MODE:</span>
            <span className="text-cyan-300">{modes[mode as keyof typeof modes].label}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">STABILITY_INDEX (N4):</span>
            <span className="text-white">1.000</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">COHERENCE (N20):</span>
            <span className="text-white">0.994</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">ADAPTIVE_GAIN (N13):</span>
            <span className="text-white">α/α₀ 1.199</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">BACKREACTION (N9):</span>
            <span className={`transition-colors ${mode === 'RUNAWAY' ? 'text-red-500 animate-pulse' : 'text-white'}`}>
              1.297e+07
            </span>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-2">
          {Object.keys(modes).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`py-2 text-[9px] border transition-all ${
                mode === m ? 'bg-cyan-600 border-cyan-400 text-white' : 'border-cyan-900/30 text-cyan-900 hover:border-cyan-700'
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* PHASE DIAL (N15) */}
      {mode === 'REPHASE' && (
        <div className="absolute bottom-10 right-10 z-20 flex flex-col items-center">
          <div className="w-24 h-24 border-2 border-dashed border-red-500/50 rounded-full flex items-center justify-center animate-spin-slow">
            <div className="w-1 h-12 bg-red-400 origin-bottom transform rotate-[215deg]" /> 
          </div>
          <span className="text-[10px] text-red-400 mt-2">PHASE_RELAX: -0.611 RAD</span>
        </div>
      )}

      {/* THREE.JS SCENE */}
      <mesh ref={meshRef} rotation={[-Math.PI / 3, 0, 0]}>
        <planeGeometry args={[100, 100, 128, 128]} />
        <shaderMaterial {...nSeriesShader} transparent />
      </mesh>

      <ambientLight intensity={0.2} />
      <pointLight position={[10, 10, 10]} intensity={1} color="#00ffff" />
    </div>
  );
}