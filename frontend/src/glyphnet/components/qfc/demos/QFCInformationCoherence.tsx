"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html as DreiHtml } from "@react-three/drei";
import * as THREE from "three";

/**
 * Vol-IV: Information Coherence Phase-Lock
 * Design Soul: Wormhole / Geometric Emergence
 * Palette: Violet (Entropy) -> Cyan -> White (Information)
 */

const vol4CoherenceShader = {
  uniforms: {
    uTime: { value: 0 },
    uCoherence: { value: 0 },   // C_phi (0..1)
    uDispersion: { value: 1.0 }, // D_phi (1..0)
    uBrightness: { value: 1.05 },
  },
  vertexShader: `
    varying float vDistance;
    varying float vC;
    uniform float uTime;
    uniform float uCoherence;
    uniform float uDispersion;

    void main() {
      vec3 pos = position;

      // Calculate angle from x/z plane
      float angle = atan(pos.z, pos.x);

      // WORMHOLE SOUL: Turbulence that collapses as dispersion (D_phi) hits 0.
      float turbulence = sin(angle * 8.0 + uTime * 2.0) * cos(angle * 3.0 - uTime);
      float ripple = turbulence * uDispersion * 1.5;

      // Base radius locks to 3.5 as coherence rises
      float radius = 3.5 + ripple;

      pos.x = cos(angle) * radius;
      pos.z = sin(angle) * radius;

      // Vertical "breathing" phase
      pos.y += 0.15 * sin(uTime * 1.2 + angle * 4.0) * (0.1 + 0.9 * uCoherence);

      vDistance = radius;
      vC = uCoherence;

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;

      // Dynamic point sizing: expands as information emerges
      gl_PointSize = 1.6 + (uCoherence * 3.4);
    }
  `,
  fragmentShader: `
    varying float vDistance;
    varying float vC;
    uniform float uBrightness;

    void main() {
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      // WORMHOLE PALETTE GUIDE:
      vec3 entropyColor = vec3(0.4, 0.15, 1.0);  // Violet (High Entropy)
      vec3 cyanColor    = vec3(0.0, 0.85, 1.0);  // Cyan (Emergent State)
      vec3 infoColor    = vec3(0.85, 0.85, 1.0); // Soft White (Phase Locked)

      // Color mapping: Shift from Violet to Cyan to White based on C_phi
      vec3 base = mix(entropyColor, cyanColor, vC);
      vec3 finalColor = mix(base, infoColor, pow(vC, 3.0));

      // Glow logic: Tightly bound to the ring shell
      float shell = smoothstep(3.0, 4.0, vDistance);
      float glow = pow(vC, 1.8) * (0.2 + 0.8 * shell) * uBrightness;
      
      float alpha = clamp(0.22 + glow, 0.0, 0.9);

      gl_FragColor = vec4(finalColor * (0.8 + glow), alpha);
    }
  `,
};

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

export default function QFCInformationCoherenceV2({ frame }: { frame?: any }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const tRef = useRef(0);
  const cSm = useRef(0);

  // High-density 4000 node particle ring
  const geometry = useMemo(() => {
    const count = 4000;
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      pos[i * 3 + 0] = Math.cos(theta);
      pos[i * 3 + 1] = (Math.random() - 0.5) * 0.05;
      pos[i * 3 + 2] = Math.sin(theta);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    return geo;
  }, []);

  useEffect(() => {
    return () => geometry.dispose();
  }, [geometry]);

  useFrame((_state, dtRaw) => {
    if (!materialRef.current) return;
    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;
    
    const mat = materialRef.current;
    mat.uniforms.uTime.value = tRef.current;

    // Convergence logic: target 0.953 over 8 seconds
    const targetC = clamp01(tRef.current / 8) * 0.953;
    const lerp = 1 - Math.exp(-dtc * 8.0);
    cSm.current += (targetC - cSm.current) * lerp;

    mat.uniforms.uCoherence.value = cSm.current;
    mat.uniforms.uDispersion.value = 1.0 - cSm.current;
    mat.uniforms.uBrightness.value = 1.02 + 0.08 * Math.sin(tRef.current * 0.5);
  });

  const lockId = frame?.lock_id ?? "VolIV-PHASE-LOCK-v2.0";

  return (
    <group position={[0, 0.2, 0]}>
      <DreiHtml fullscreen transform={false} zIndexRange={[100, 0]}>
        <div className="pointer-events-none w-full h-full font-mono">
          <div className="absolute top-10 left-10 pointer-events-auto p-5 border border-cyan-500/20 bg-black/60 backdrop-blur-lg rounded shadow-2xl w-80">
            <div className="flex justify-between items-center border-b border-cyan-900/40 pb-2 mb-4">
              <span className="text-cyan-400 font-bold text-[10px] tracking-[0.2em] uppercase">
                VOL4_COHERENCE
              </span>
              <span className="text-[8px] text-cyan-800">TRACE: {lockId.slice(0, 8)}</span>
            </div>

            <div className="space-y-3">
              <div className="space-y-1">
                <div className="flex justify-between text-[9px] text-slate-400">
                  <span>METRIC: C_phi</span>
                  <span className="text-cyan-300">{cSm.current.toFixed(4)}</span>
                </div>
                <div className="h-1 w-full bg-cyan-950/50 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-cyan-400 shadow-[0_0_8px_rgba(0,255,255,0.5)] transition-all duration-100" 
                    style={{ width: `${(cSm.current / 0.953) * 100}%` }} 
                  />
                </div>
              </div>

              <div className="pt-2 text-[9px] text-slate-300 leading-relaxed opacity-80">
                <p>IDENTITY: I = 1 − D_phi</p>
                <p className="text-cyan-200">STATE: {cSm.current > 0.9 ? "PASS (LOCKED)" : "EMERGENT"}</p>
              </div>
            </div>

            <div className="mt-6 text-[8px] text-slate-500 uppercase tracking-widest border-t border-white/5 pt-3">
              Entropy Decay → Information Emergence
            </div>
          </div>
        </div>
      </DreiHtml>

      <points geometry={geometry}>
        <shaderMaterial
          ref={materialRef}
          {...vol4CoherenceShader}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </points>

      {/* Internal "Information Core" glow */}
      <pointLight 
        position={[0, 1, 0]} 
        intensity={0.4 * cSm.current} 
        color="#00f2ff" 
        distance={10} 
      />
    </group>
  );
}