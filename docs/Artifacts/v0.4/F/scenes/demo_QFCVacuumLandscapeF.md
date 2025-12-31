"use client";

import React, { useMemo, useRef, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Text, Sphere, Line } from "@react-three/drei";
import * as THREE from "three";

/**
 * SOURCE-OF-TRUTH: RUN_ID F20251231T000030Z_F
 * PINNED ARTIFACTS: 
 * - F13G9_singularity_resolution.json (a_min ≈ 0.8847)
 * - F18_landscape_equilibrium.json (Spread ≈ 2.23e-15)
 * - F7bR_entropy_flux.json (Anti-Corr ≈ 0.947)
 */

const PINNED_METRICS = {
  a_min: 0.88466, // F13/G9 Bridge Floor
  lambda_eq: 0.99999997, // F18 Convergence
  lambda_spread: 2.23e-15, // F18 Synchronization
  entropy_flux: 0.000238, // F7bR Baseline
  anti_corr: 0.947, // I/F Feedback proxy
  damping_zeta: 1.0, // F18 Controller
};

// --- Cosmological Shader: Scale Factor & Curvature Density ---
const VacuumShader = {
  uniforms: {
    uTime: { value: 0 },
    uScaleFactor: { value: 1.0 },
    uCurvatureIntensity: { value: 0.0 },
    uSyncLevel: { value: 0.0 },
  },
  vertexShader: `
    varying vec3 vPosition;
    varying float vDist;
    uniform float uScaleFactor;
    uniform float uTime;

    void main() {
      vPosition = position;
      // Apply scale factor a(t) to the geometry
      vec3 scaledPos = position * uScaleFactor;
      
      // Add micro-fluctuations (Vacuum noise)
      scaledPos += sin(scaledPos * 5.0 + uTime) * 0.02;
      
      vDist = length(position);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(scaledPos, 1.0);
    }
  `,
  fragmentShader: `
    varying vec3 vPosition;
    varying float vDist;
    uniform float uCurvatureIntensity;
    uniform float uSyncLevel;

    void main() {
      // Color shifts from deep void (blue) to high-density bridge (orange/white)
      vec3 voidColor = vec3(0.05, 0.1, 0.3);
      vec3 bridgeColor = vec3(1.0, 0.6, 0.2);
      
      // Sync visual: domains become uniform as uSyncLevel -> 1.0
      vec3 domainSync = mix(vec3(0.5), vec3(1.0), uSyncLevel);
      
      vec3 finalColor = mix(voidColor, bridgeColor, uCurvatureIntensity * (1.0 - vDist * 0.5));
      gl_FragColor = vec4(finalColor * domainSync, 0.8);
    }
  `
};

const QuantumBridge = ({ scale }: { scale: number }) => {
  const meshRef = useRef<THREE.Mesh>(null!);
  const uniforms = useMemo(() => THREE.UniformsUtils.clone(VacuumShader.uniforms), []);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    // Simulate cyclic scale factor a(t) around the neck
    // Maps to FAEV_F13G9_ScaleFactor.png profile
    const a_t = PINNED_METRICS.a_min + (1.0 - PINNED_METRICS.a_min) * (0.5 + 0.5 * Math.cos(t * 0.8));
    
    // Curvature intensity peaks at a_min (The Bridge)
    const curvature = Math.pow(1.0 - (a_t - PINNED_METRICS.a_min) / (1.0 - PINNED_METRICS.a_min), 4.0);
    
    uniforms.uTime.value = t;
    uniforms.uScaleFactor.value = a_t;
    uniforms.uCurvatureIntensity.value = curvature * 0.8;
    // F18 Convergence progress
    uniforms.uSyncLevel.value = Math.min(t / 20.0, 1.0);
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[5, 64, 64]} />
      <shaderMaterial {...VacuumShader} uniforms={uniforms} transparent wireframe />
    </mesh>
  );
};

export default function QFCVacuumLandscapeF() {
  const [telemetry, setTelemetry] = useState({ eFlux: 0, sFlux: 0 });

  useEffect(() => {
    const interval = setInterval(() => {
      const t = Date.now() / 1000;
      // Model I/F Anti-correlation: E(t) rising as S(t) falls
      const e = 0.5 + 0.5 * Math.sin(t * 0.8);
      const s = (1.0 - e) * PINNED_METRICS.anti_corr;
      setTelemetry({ eFlux: e, sFlux: s });
    }, 50);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full h-screen bg-[#020205] text-[#a0c0ff] font-mono overflow-hidden flex">
      {/* LEFT: COSMOLOGICAL VIEWPORT */}
      <div className="w-3/4 h-full relative">
        <Canvas camera={{ position: [12, 8, 12], fov: 45 }}>
          <OrbitControls />
          <ambientLight intensity={0.2} />
          <pointLight position={[10, 10, 10]} intensity={1.5} color="#ffaa44" />
          
          <QuantumBridge scale={1.0} />
          
          {/* F18 Multi-Domain Landscape (Sub-attractors) */}
          {[...Array(6)].map((_, i) => (
            <group key={i} rotation={[0, (i * Math.PI) / 3, 0]}>
              <Sphere args={[0.2, 16, 16]} position={[8, Math.sin(i), 0]}>
                <meshStandardMaterial color="#44aaff" emissive="#002244" />
              </Sphere>
            </group>
          ))}
        </Canvas>

        <div className="absolute top-6 left-6 p-4 border border-[#1e293b] bg-black/80 backdrop-blur-md">
          <h2 className="text-sm font-bold tracking-widest text-[#60a5fa]">F-SERIES: COSMIC_BOUNCE</h2>
          <p className="text-[10px] text-slate-500">RUN_ID: F20251231T000030Z_F</p>
          <div className="mt-4 space-y-1 text-[11px]">
            <div className="flex justify-between gap-8">
              <span>NECK_FLOOR (a_min):</span>
              <span className="text-white">{PINNED_METRICS.a_min.toFixed(5)}</span>
            </div>
            <div className="flex justify-between">
              <span>CONVERGENCE (Λ_eq):</span>
              <span className="text-emerald-400">{PINNED_METRICS.lambda_eq.toFixed(3)}</span>
            </div>
            <div className="flex justify-between">
              <span>LQC_STATUS:</span>
              <span className="text-blue-400">RESOLVED</span>
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT: HUD (I/F FEEDBACK GAUGES) */}
      <div className="w-1/4 h-full border-l border-[#1e293b] p-8 flex flex-col gap-10 bg-[#05050a]">
        <header>
          <p className="text-[10px] uppercase tracking-widest text-slate-500">I/F Feedback Note</p>
          <h1 className="text-lg font-bold text-white">Vacuum Dynamics</h1>
        </header>

        {/* ENERGY FLUX (E) */}
        <div className="space-y-2">
          <div className="flex justify-between text-[10px]">
            <span>ENERGY_FLUX (E)</span>
            <span>{telemetry.eFlux.toFixed(4)}</span>
          </div>
          <div className="h-2 bg-slate-900 overflow-hidden border border-slate-800">
            <div 
              className="h-full bg-orange-500 transition-all duration-75" 
              style={{ width: `${telemetry.eFlux * 100}%` }}
            />
          </div>
        </div>

        {/* ENTROPY FLUX (S) - ANTI-CORRELATED */}
        <div className="space-y-2">
          <div className="flex justify-between text-[10px]">
            <span>ENTROPY_FLUX (S)</span>
            <span>{telemetry.sFlux.toFixed(4)}</span>
          </div>
          <div className="h-2 bg-slate-900 overflow-hidden border border-slate-800">
            <div 
              className="h-full bg-cyan-500 transition-all duration-75" 
              style={{ width: `${telemetry.sFlux * 100}%` }}
            />
          </div>
          <p className="text-[9px] text-slate-600 italic">Anti-Correlation ρ ≈ -0.95</p>
        </div>

        <div className="mt-auto space-y-4 border-t border-slate-800 pt-6">
          <div className="p-3 bg-slate-900/50 border border-slate-800">
            <p className="text-[9px] text-slate-400 leading-relaxed">
              F18 LANDSCAPE_CONVERGENCE:<br/>
              Residual Spread: {PINNED_METRICS.lambda_spread.toExponential(2)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
            <span className="text-[10px] text-emerald-500 uppercase">System Coherent</span>
          </div>
        </div>
      </div>
    </div>
  );
}