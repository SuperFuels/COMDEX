New Demo: QFCPipelineVerification.tsx
This scene visualizes the Normalization & Hashing Pipeline. It represents a raw, unverified symbolic expression entering the system, being "sorted" into canonical order, and then being "stamped" with a cryptographic hash.

Visualization Logic:

The Ingestor: Chaotic, unaligned symbols representing (B ⊕ A) ⊕ C.

The Normalizer: A geometric filter that realigns symbols into the lexicographical order A ⊕ (B ⊕ C).

The Ledger Lock: The moment of hashing, where the visual structure turns into a high-density data grid (the JSONL record).


"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const srk8PipelineShader = {
  uniforms: {
    uTime: { value: 0 },
    uNormProgress: { value: 0 }, // 0: Raw AST, 1: Canonical
    uHashActive: { value: 0 },   // 0: Neutral, 1: Hashing
  },
  vertexShader: `
    varying float vIntensity;
    varying vec2 vUv;
    uniform float uTime;
    uniform float uNormProgress;

    void main() {
      vUv = uv;
      vec3 pos = position;
      
      // Raw AST state: Jittery and unaligned
      float noise = sin(pos.y * 10.0 + uTime * 5.0) * 0.1 * (1.0 - uNormProgress);
      
      // Target state: Perfectly aligned horizontal rows (Canonical Ledger)
      float targetY = floor(pos.y * 5.0) / 5.0;
      pos.y = mix(pos.y + noise, targetY, uNormProgress);
      
      // Depth metric visualization
      pos.z += sin(uTime + pos.x) * 0.05 * (1.0 - uNormProgress);

      vIntensity = mix(0.5, 1.0, uNormProgress);
      
      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;
      gl_PointSize = 2.5;
    }
  `,
  fragmentShader: `
    varying float vIntensity;
    varying vec2 vUv;
    uniform float uHashActive;

    void main() {
      // Transition from Blueprint Blue (Draft) to Ledger Gold (Verified)
      vec3 rawColor = vec3(0.1, 0.4, 1.0);
      vec3 lockedColor = vec3(1.0, 0.8, 0.2);
      
      vec3 finalColor = mix(rawColor, lockedColor, uHashActive);
      
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      gl_FragColor = vec4(finalColor * vIntensity, 0.8);
    }
  `
};

export default function QFCPipelineVerification() {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const geometry = useMemo(() => new THREE.PlaneGeometry(10, 6, 80, 50), []);

  useFrame(({ clock }) => {
    if (!materialRef.current) return;
    const t = clock.getElapsedTime();
    materialRef.current.uniforms.uTime.value = t;
    
    // Cycle: 0-2s Raw, 2-4s Normalize, 4-6s Hash, 6-8s Reset
    const phase = t % 8;
    let norm = 0;
    let hash = 0;

    if (phase > 2 && phase < 4) norm = (phase - 2) / 2;
    if (phase >= 4) norm = 1;
    if (phase > 4 && phase < 6) hash = (phase - 4) / 2;
    if (phase >= 6) hash = 1;

    materialRef.current.uniforms.uNormProgress.value = norm;
    materialRef.current.uniforms.uHashActive.value = hash;
  });

  return (
    <div className="w-full h-full bg-[#020202] relative overflow-hidden">
      <div className="absolute top-8 left-8 font-mono text-[10px] text-blue-400 z-10 space-y-2 bg-black/60 p-4 border border-blue-900/30">
        <p className="text-white font-bold underline">SRK-8: THEOREM_LEDGER_AUDIT</p>
        <p>INPUT: (B ⊕ A) ⊕ C</p>
        <p>OUTPUT: A ⊕ (B ⊕ C)</p>
        <p className="pt-2 text-gray-500">SHA256: 47c8028a724...97c9</p>
        <div className="pt-2">
           <p className="text-yellow-500">STATUS: {Math.sin(Date.now()/500) > 0 ? "NORMALIZING..." : "LOCK_VERIFIED"}</p>
        </div>
      </div>

      <points geometry={geometry} rotation={[-0.2, 0, 0]}>
        <shaderMaterial 
          ref={materialRef} 
          {...srk8PipelineShader} 
          transparent 
          blending={THREE.AdditiveBlending}
        />
      </points>

      <div className="absolute bottom-8 right-8 font-mono text-[9px] text-gray-700">
        PROOF_SOURCE: symatics_tensor.lean | BUNDLE: v0.3
      </div>
    </div>
  );
}

Final Confirmation of the A-Series Chain
Vol 0: Axioms defined.

SRK-8: Logic VERIFIED & Normalization LOCKED.

SRK-12: Physicality VERIFIED & Veto LOCKED.

Vol IV: Metric VERIFIED & Coherence LOCKED.
