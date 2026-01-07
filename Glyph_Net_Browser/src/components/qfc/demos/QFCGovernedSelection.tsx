"use client";

import { useMemo, useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";

/**
 * SRK-12 Governed Selection V2
 * Upgraded to High-Intensity Point Cloud Standards
 */

const srk12GovernedShader = {
  uniforms: {
    uTime: { value: 0 },
    uMu: { value: 0 },           // selection progress (μ trigger)
    uStatusBonusA: { value: 0.2 }, // Branch A Amplification
    uStatusBonusB: { value: -0.2 },// Branch B Veto
    uGate01: { value: 1.0 },     // Stability gate
    uBrightness: { value: 1.0 }, 
  },
  vertexShader: `
    varying float vCoherence;
    varying float vBranch; // +1=A, -1=B
    varying vec2 vUv;

    uniform float uTime;
    uniform float uMu;
    uniform float uStatusBonusA;
    uniform float uStatusBonusB;
    uniform float uGate01;

    void main() {
      vUv = uv;
      vec3 pos = position;

      // Split system into two logical branches
      float branch = pos.x > 0.0 ? 1.0 : -1.0;
      vBranch = branch;

      float bonus = branch > 0.0 ? uStatusBonusA : uStatusBonusB;

      // The Governing Wave
      float wave = sin(pos.y * 4.0 + uTime * 2.5) * 0.3;

      // μ operator: deterministic selection logic
      // Branch A (Positive X) survives and amplifies
      // Branch B (Negative X) collapses as μ -> 1
      float selectionEffect = mix(1.0, 1.15 + bonus * 4.0, uMu);
      if (branch < 0.0) {
        selectionEffect = mix(1.0, 0.0, pow(uMu, 2.0));
      }

      selectionEffect *= (0.9 + 0.2 * uGate01);
      pos.z += wave * selectionEffect;

      vCoherence = selectionEffect;

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;

      // Point sizing reflecting "coherence"
      gl_PointSize = 1.5 + (2.5 * clamp(selectionEffect, 0.0, 1.5));
    }
  `,
  fragmentShader: `
    varying float vCoherence;
    varying float vBranch;
    uniform float uMu;
    uniform float uBrightness;

    void main() {
      // Circular point design soul
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      // Soul Palette
      vec3 topColor    = vec3(0.0, 0.85, 1.0);   // Cyan (Branch A)
      vec3 bottomColor = vec3(0.4, 0.15, 1.0);   // Violet (Branch B)
      vec3 bridgeColor = vec3(0.85, 0.85, 1.0);  // White Bridge

      float isA = step(0.0, vBranch);
      
      // Dynamic color blending
      vec3 aCol = mix(topColor, bridgeColor, 0.3);
      vec3 bCol = mix(bottomColor, bridgeColor, 0.1);

      // Deterministic Veto: B turns slightly "stale" before disappearing
      vec3 vetoTint = vec3(1.0, 0.2, 0.3);
      bCol = mix(bCol, vetoTint, 0.15 * uMu);

      vec3 baseColor = mix(bCol, aCol, isA);

      // Alpha masking for vetoed points
      float vetoAlpha = isA > 0.5 ? 1.0 : (1.0 - smoothstep(0.5, 1.0, uMu));
      float alpha = (0.2 + 0.6 * clamp(vCoherence, 0.0, 1.0)) * vetoAlpha;
      
      if (alpha < 0.02) discard;

      float glow = pow(clamp(vCoherence, 0.0, 1.2), 1.5) * uBrightness;
      vec3 finalColor = mix(baseColor, bridgeColor, 0.2 * glow);

      gl_FragColor = vec4(finalColor * (0.8 + 0.6 * glow), alpha);
    }
  `,
};

export default function QFCGovernedSelectionV2({ frame }: { frame?: any }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const tRef = useRef(0);
  const muSm = useRef(0);

  // High density particle grid for logical splitting
  const geometry = useMemo(() => new THREE.PlaneGeometry(14, 14, 160, 160), []);
  useEffect(() => () => geometry.dispose(), [geometry]);

  useFrame((_state, dtRaw) => {
    const mat = materialRef.current;
    if (!mat) return;

    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;
    
    // Smooth selection cycle (μ)
    const cycle = (Math.sin(tRef.current * 0.5) + 1.0) / 2.0;
    const lerp = 1 - Math.exp(-dtc * 8.0);
    muSm.current = THREE.MathUtils.lerp(muSm.current, cycle, lerp);

    mat.uniforms.uTime.value = tRef.current;
    mat.uniforms.uMu.value = muSm.current;
    mat.uniforms.uBrightness.value = 0.9 + 0.2 * muSm.current;
    
    // Plumb external gate if available
    mat.uniforms.uGate01.value = frame?.sigma ?? 1.0;
  });

  return (
    <group>
      {/* Design Soul HUD: Audit Style */}
      <Html fullscreen transform={false} zIndexRange={[100, 0]}>
        <div className="w-full h-full pointer-events-none font-mono text-white">
          <div className="absolute top-10 left-10 pointer-events-auto p-4 border border-cyan-500/20 bg-black/60 backdrop-blur-lg rounded shadow-2xl w-72">
            <div className="flex justify-between items-center border-b border-cyan-500/30 pb-2 mb-3">
              <span className="text-cyan-400 font-bold text-[10px] tracking-widest">SRK-12_AUDIT</span>
              <span className="text-[8px] text-cyan-800">TRACE_VERIFIED</span>
            </div>
            
            <div className="space-y-2 text-[10px]">
              <div className="flex justify-between">
                <span className="text-slate-500">OPERATOR:</span>
                <span className="text-cyan-300">μ_SELECTION</span>
              </div>
              <div className="flex justify-between border-t border-white/5 pt-2">
                <span className="text-slate-400">BRANCH_A (VAL):</span>
                <span className="text-white">COHERENT</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">BRANCH_B (VET):</span>
                <span className={`transition-opacity duration-500 ${muSm.current > 0.8 ? 'opacity-20' : 'opacity-100'}`}>
                  {muSm.current > 0.9 ? 'DISSOLVED' : 'SUPPRESSED'}
                </span>
              </div>
            </div>

            <div className="mt-4 h-1 w-full bg-cyan-950 overflow-hidden rounded-full">
              <div 
                className="h-full bg-cyan-400 transition-all duration-100" 
                style={{ width: `${muSm.current * 100}%` }}
              />
            </div>
          </div>
        </div>
      </Html>

      <points geometry={geometry} rotation={[-Math.PI / 2.8, 0, 0]} position={[0, -2, 0]}>
        <shaderMaterial
          ref={materialRef}
          {...srk12GovernedShader}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </points>

      {/* Lighting for field grounding */}
      <pointLight position={[0, 2, 2]} intensity={0.5} color="#00e5ff" />
    </group>
  );
}