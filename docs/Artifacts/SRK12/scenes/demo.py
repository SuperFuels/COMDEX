"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

/**
 * SRK-12 Governed Selection Shader
 * Implements policy-modulated Born sampling with deterministic veto.
 */
const srk12GovernedShader = {
  uniforms: {
    uTime: { value: 0 },
    uSelectionProgress: { value: 0 }, 
    uStatusBonusA: { value: 0.2 }, // Valid Bonus
    uStatusBonusB: { value: -0.2 }, // Contradiction Veto
  },
  vertexShader: `
    varying float vCoherence;
    varying vec2 vUv;
    uniform float uTime;
    uniform float uSelectionProgress;
    uniform float uStatusBonusA;
    uniform float uStatusBonusB;

    void main() {
      vUv = uv;
      vec3 pos = position;
      
      // Binary Branch Split
      float branchDir = pos.x > 0.0 ? 1.0 : -1.0;
      float bonus = branchDir > 0.0 ? uStatusBonusA : uStatusBonusB;
      
      // Wave Dynamics: Superposition (Initial) vs Collapse (Final)
      float wave = sin(pos.y * 5.0 + uTime * 3.0) * 0.2;
      
      // The mu (μ) Operator Effect
      // Branch B is vetoed (flattened to zero) as progress -> 1.0
      float selectionEffect = mix(1.0, 1.0 + bonus * 5.0, uSelectionProgress);
      if (branchDir < 0.0) { 
         selectionEffect = mix(1.0, 0.0, uSelectionProgress);
      }
      
      pos.z += wave * selectionEffect;
      vCoherence = selectionEffect;
      
      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;
      gl_PointSize = 1.8;
    }
  `,
  fragmentShader: `
    varying float vCoherence;
    varying vec2 vUv;

    void main() {
      vec3 branchAColor = vec3(0.0, 1.0, 0.85); // Neon Cyan
      vec3 branchBColor = vec3(0.8, 0.1, 0.3); // Veto Red
      
      vec3 finalColor = vUv.x > 0.5 ? branchAColor : branchBColor;
      
      // High-precision alpha for "contradiction suppression"
      float alpha = clamp(vCoherence, 0.0, 1.0);
      if (alpha < 0.01) discard;

      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      gl_FragColor = vec4(finalColor * (vCoherence + 0.5), alpha);
    }
  `
};

export default function QFCGovernedSelection({ frame }: { frame: any }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const geometry = useMemo(() => new THREE.PlaneGeometry(12, 12, 128, 128), []);

  useFrame(({ clock }) => {
    if (!materialRef.current) return;
    const t = clock.getElapsedTime();
    materialRef.current.uniforms.uTime.value = t;
    
    // Simulation of the mu-operator trigger (collapse cycle)
    const cycle = (Math.sin(t * 0.4) + 1.0) / 2.0;
    materialRef.current.uniforms.uSelectionProgress.value = cycle;
  });

  return (
    <div className="relative w-full h-full bg-[#050505]">
      {/* HUD: Truth Chain Audit */}
      <div className="absolute top-6 left-6 font-mono text-[11px] text-cyan-300 z-10 p-3 border border-cyan-900/50 bg-black/80 backdrop-blur-md">
        <p className="font-bold border-b border-cyan-900 pb-1 mb-2">AUDIT: SRK-12-VERIFIED</p>
        <p>OP: μ (Governed Selection)</p>
        <p>REPLAY_ID: {frame?.lock_id ?? "SRK12-TRACE-001"}</p>
        <div className="mt-2 space-y-1">
          <p className="text-white">BRANCH_A: 1.0 (VALID)</p>
          <p className="text-red-500">BRANCH_B: 0.0 (VETOED)</p>
          <p className="text-gray-400">DET_RATIO: 1.0000000</p>
        </div>
      </div>

      <points geometry={geometry} rotation={[-Math.PI / 2.5, 0, 0]}>
        <shaderMaterial 
          ref={materialRef} 
          {...srk12GovernedShader} 
          transparent 
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </points>
    </div>
  );
}