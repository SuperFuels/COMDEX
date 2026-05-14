"use client";

import { useMemo, useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";

/**
 * K-SERIES: CAUSAL SPACETIME MESH
 * Logic: K3b Gaussian Soliton + K1 Causal Cone Constraint
 * Soul: Volumetric Wire-Point Cloud (Violet -> Cyan -> White)
 */

const kSeriesShader = {
  uniforms: {
    uTime: { value: 0 },
    uCeff: { value: 0.7071 }, // C_phi speed of light/information
    uBrightness: { value: 1.0 },
  },
  vertexShader: `
    varying float vIntensity;
    varying float vConeAlpha;
    varying vec2 vUv;

    uniform float uTime;
    uniform float uCeff;

    void main() {
      vUv = uv;
      vec3 pos = position;

      // Spacetime Coordinates: X is space, Y is time-axis
      float x = pos.x;
      float t_axis = pos.y + 5.0; // Offset to start cone at bottom

      // K3b: Gaussian Soliton Drifting (-0.0028 velocity) (scaled for viz)
      float drift = -0.056 * uTime; // visual scale; preserves directionality
      float sol_x = x - drift;
      float soliton = exp(-0.1 * pow(sol_x, 2.0));

      // K1: Causal Cone Constraint
      float coneWidth = uCeff * t_axis;
      // inCone ~ 1 when |x| <= coneWidth, smooth boundary
      float inCone = smoothstep(coneWidth + 0.5, coneWidth - 0.5, abs(x));

      // Displace Z based on soliton intensity inside the cone
      pos.z += soliton * inCone * 2.5;

      vIntensity = soliton;
      vConeAlpha = inCone;

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;

      // Point size pulses with soliton drift — clamp for GPU stability
      float ps = (1.2 + (soliton * 2.5)) * (0.8 + 0.2 * inCone);
      gl_PointSize = clamp(ps, 0.5, 6.0);
    }
  `,
  fragmentShader: `
    varying float vIntensity;
    varying float vConeAlpha;
    varying vec2 vUv;

    uniform float uBrightness;

    void main() {
      // Round points
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      // Vol-VII Palette (kept)
      vec3 bgViolet = vec3(0.3, 0.1, 0.8);   // Entropy/Vacuum
      vec3 solCyan  = vec3(0.0, 0.9, 1.0);   // Soliton/Information
      vec3 bridge   = vec3(0.9, 0.9, 1.0);   // Causal Core

      // Base color depends on intensity; outside cone stays darker
      vec3 color = mix(bgViolet * 0.2, solCyan, vIntensity);

      // Inside the cone, push toward bridge white
      vec3 finalColor = mix(color, bridge, vIntensity * vConeAlpha * 0.6);

      // Mesh/grid overlay (kept)
      float grid =
        step(0.98, fract(vUv.x * 20.0)) +
        step(0.98, fract(vUv.y * 20.0));

      float alpha = clamp(0.15 + (vIntensity * 0.8) + (vConeAlpha * 0.2), 0.0, 0.9);

      vec3 outCol = finalColor * (0.8 + (grid * 0.4)) * uBrightness;

      gl_FragColor = vec4(outCol, alpha);
    }
  `,
};

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const num = (v: any, d: number) => (Number.isFinite(Number(v)) ? Number(v) : d);

export default function QFCCausalSpacetimeK({ frame }: { frame?: any }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  // ✅ dt clamp + stable time accumulator
  const tRef = useRef(0);

  // High resolution point grid
  const geometry = useMemo(() => new THREE.PlaneGeometry(10, 10, 128, 128), []);
  useEffect(() => () => geometry.dispose(), [geometry]);

  useFrame((_state, dtRaw) => {
    const mat = materialRef.current;
    if (!mat) return;

    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;

    // stable time, keep your mod 10 loop
    const t = tRef.current % 10;
    mat.uniforms.uTime.value = t;

    // Signal plumbing (safe)
    const ceffRaw = num(frame?.c_eff ?? frame?.ceff, 0.7071);
    // keep ceff within sensible range so coneWidth doesn't go negative/huge
    const ceff = Math.max(0.05, Math.min(1.25, ceffRaw));

    // smooth to avoid stepping
    const lerp = 1 - Math.exp(-dtc * 10.0);
    mat.uniforms.uCeff.value = mat.uniforms.uCeff.value + (ceff - mat.uniforms.uCeff.value) * lerp;

    // subtle brightness breathing (kept)
    mat.uniforms.uBrightness.value = 1.0 + Math.sin(tRef.current * 0.5) * 0.05;
  });

  return (
    <group rotation={[-Math.PI / 3, 0, 0]} position={[0, -1, 0]}>
      {/* HUD Architecture (DOM is ONLY inside Html) */}
      <Html fullscreen transform={false} zIndexRange={[100, 0]}>
        <div className="pointer-events-none w-full h-full font-mono text-white">
          <div className="absolute top-10 left-10 p-5 border border-cyan-500/20 bg-black/60 backdrop-blur-md rounded w-72 pointer-events-auto">
            <div className="border-b border-cyan-800/40 pb-2 mb-4">
              <span className="text-cyan-400 font-bold text-[10px] tracking-widest uppercase">
                K-SERIES // SPACETIME
              </span>
            </div>

            <div className="space-y-2 text-[9px] text-slate-400">
              <div className="flex justify-between">
                <span>CAUSAL_EFF (C_eff):</span>
                <span className="text-cyan-300">
                  {Number.isFinite(Number(frame?.c_eff ?? frame?.ceff))
                    ? Number(frame?.c_eff ?? frame?.ceff).toFixed(4)
                    : "0.7071"}
                </span>
              </div>
              <div className="flex justify-between">
                <span>SOLITON_DRIFT (v):</span>
                <span className="text-white">-0.0028</span>
              </div>
              <div className="flex justify-between border-t border-white/5 pt-2 mt-2">
                <span className="text-slate-500">CONSTRAINT:</span>
                <span className="text-violet-400">|x| ≤ C_eff · t</span>
              </div>
            </div>
          </div>

          <div className="absolute bottom-10 right-10 text-[8px] text-slate-500/50 text-right uppercase tracking-tighter">
            Volumetric Mesh: 128x128 Nodes
            <br />
            Phase: Locked & Deterministic
          </div>
        </div>
      </Html>

      <points geometry={geometry}>
        <shaderMaterial
          ref={materialRef}
          uniforms={kSeriesShader.uniforms}
          vertexShader={kSeriesShader.vertexShader}
          fragmentShader={kSeriesShader.fragmentShader}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </points>

      {/* Subtle fill light to define the soliton peak */}
      <pointLight position={[0, 0, 2]} intensity={0.4} color="#00ffff" />
    </group>
  );
}