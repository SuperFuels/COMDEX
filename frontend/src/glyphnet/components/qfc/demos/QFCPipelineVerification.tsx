"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html as DreiHtml } from "@react-three/drei";
import * as THREE from "three";

const srk8PipelineShader = {
  uniforms: {
    uTime: { value: 0 },
    uNormProgress: { value: 0 }, // 0: Raw AST, 1: Canonical
    uHashActive: { value: 0 }, // 0: Neutral, 1: Hashing
    uBrightness: { value: 1.0 },
  },
  vertexShader: `
    varying float vIntensity;
    varying vec2 vUv;
    uniform float uTime;
    uniform float uNormProgress;

    void main() {
      vUv = uv;
      vec3 pos = position;

      // Raw AST: jitter + slight depth wobble
      float noise = sin(pos.y * 10.0 + uTime * 5.0) * 0.1 * (1.0 - uNormProgress);

      // Canonical: snap to aligned rows
      float targetY = floor(pos.y * 5.0) / 5.0;
      pos.y = mix(pos.y + noise, targetY, uNormProgress);

      // Depth metric visualization fades out as canonicalization completes
      pos.z += sin(uTime + pos.x) * 0.05 * (1.0 - uNormProgress);

      // intensity ramps with normalization (stable)
      vIntensity = mix(0.55, 1.0, uNormProgress);

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;

      // Slightly tighter points (keeps it crisp in your grid)
      gl_PointSize = 2.1;
    }
  `,
  fragmentShader: `
    varying float vIntensity;
    varying vec2 vUv;
    uniform float uHashActive;
    uniform float uBrightness;

    void main() {
      // Blueprint Blue -> Ledger Gold (subtle)
      vec3 rawColor   = vec3(0.12, 0.38, 0.95);
      vec3 lockedGold = vec3(1.00, 0.84, 0.28);

      vec3 col = mix(rawColor, lockedGold, uHashActive);

      // round points
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      // mild glow (no neon blowout)
      float glow = 0.15 + 0.35 * vIntensity + 0.15 * uHashActive;
      float alpha = clamp(0.35 + 0.35 * vIntensity + 0.15 * uHashActive, 0.0, 0.95);

      gl_FragColor = vec4(col * (0.85 + glow) * uBrightness, alpha);
    }
  `,
};

export default function QFCPipelineVerification({ frame }: { frame?: any }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  // ✅ dt clamp + stable time accumulator
  const tRef = useRef(0);

  // geometry: plane grid of points
  const geometry = useMemo(() => new THREE.PlaneGeometry(10, 6, 80, 50), []);
  useEffect(() => () => geometry.dispose(), [geometry]);

  // simple derived state for HUD (no per-frame React re-render)
  const hudPhaseRef = useRef<{
    label: string;
    sha: string;
  }>({
    label: "RAW_AST",
    sha: "47c8028a724...97c9",
  });

  useFrame((_state, dtRaw) => {
    const mat = materialRef.current;
    if (!mat) return;

    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;
    const t = tRef.current;

    mat.uniforms.uTime.value = t;

    // Cycle: 0-2s Raw, 2-4s Normalize, 4-6s Hash, 6-8s Verified, loop
    const phase = t % 8;
    let norm = 0;
    let hash = 0;

    if (phase > 2 && phase < 4) norm = (phase - 2) / 2;
    if (phase >= 4) norm = 1;

    if (phase > 4 && phase < 6) hash = (phase - 4) / 2;
    if (phase >= 6) hash = 1;

    mat.uniforms.uNormProgress.value = norm;
    mat.uniforms.uHashActive.value = hash;

    // gentle brightness breathing (subtle)
    mat.uniforms.uBrightness.value = 0.98 + 0.04 * Math.sin(t * 0.6);

    // HUD label (no React state churn)
    if (phase < 2) hudPhaseRef.current.label = "RAW_AST";
    else if (phase < 4) hudPhaseRef.current.label = "NORMALIZING";
    else if (phase < 6) hudPhaseRef.current.label = "HASHING";
    else hudPhaseRef.current.label = "LOCK_VERIFIED";
  });

  return (
    <group>
      {/* HUD (DOM must live in Html, NOT as <div> in the R3F tree) */}
      <DreiHtml fullscreen transform={false} zIndexRange={[100, 0]}>
        <div className="pointer-events-none w-full h-full font-mono">
          <div className="absolute top-8 left-8 pointer-events-auto text-[10px] text-blue-300 space-y-2 bg-black/60 p-4 border border-blue-900/30 backdrop-blur-sm">
            <p className="text-white font-bold underline">SRK-8: THEOREM_LEDGER_AUDIT</p>
            <p>INPUT: (B ⊕ A) ⊕ C</p>
            <p>OUTPUT: A ⊕ (B ⊕ C)</p>
            <p className="pt-2 text-gray-500">SHA256: {hudPhaseRef.current.sha}</p>
            <div className="pt-2">
              <p
                className={
                  hudPhaseRef.current.label === "LOCK_VERIFIED"
                    ? "text-yellow-400"
                    : hudPhaseRef.current.label === "HASHING"
                      ? "text-yellow-300"
                      : "text-blue-300"
                }
              >
                STATUS: {hudPhaseRef.current.label}
              </p>
            </div>
          </div>

          <div className="absolute bottom-8 right-8 text-[9px] text-gray-500/70 pointer-events-auto">
            PROOF_SOURCE: symatics_tensor.lean | BUNDLE: v0.3
          </div>
        </div>
      </DreiHtml>

      <points geometry={geometry} rotation={[-0.2, 0, 0]}>
        <shaderMaterial
          ref={materialRef}
          uniforms={srk8PipelineShader.uniforms}
          vertexShader={srk8PipelineShader.vertexShader}
          fragmentShader={srk8PipelineShader.fragmentShader}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </points>
    </group>
  );
}