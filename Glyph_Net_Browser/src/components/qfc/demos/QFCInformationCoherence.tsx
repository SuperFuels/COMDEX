"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const vol4CoherenceShader = {
  uniforms: {
    uTime: { value: 0 },
    uCoherence: { value: 0 }, // C_phi
    uDispersion: { value: 1.0 }, // D_phi
  },
  vertexShader: `
    varying float vDistance;
    varying float vCoherence;
    uniform float uTime;
    uniform float uCoherence;
    uniform float uDispersion;

    void main() {
      vec3 pos = position;
      
      // Phase angle calculation
      float angle = atan(pos.y, pos.x);
      
      // Dispersion Effect: Randomizes position based on D_phi
      // As D_phi -> 0, particles pull into a perfect circle (Phase Lock)
      float noise = sin(angle * 10.0 + uTime) * uDispersion * 2.0;
      float radius = 3.0 + noise;
      
      pos.x = cos(angle) * radius;
      pos.y = sin(angle) * radius;
      
      vDistance = radius;
      vCoherence = uCoherence;
      
      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;
      gl_PointSize = 2.0 + (uCoherence * 3.0);
    }
  `,
  fragmentShader: `
    varying float vDistance;
    varying float vCoherence;

    void main() {
      // Color Logic: 
      // High Dispersion (Entropy) = Diffuse White/Gray
      // High Coherence (Information) = Electric Gold/Yellow
      vec3 entropyColor = vec3(0.5, 0.5, 0.6);
      vec3 infoColor = vec3(1.0, 0.8, 0.2);
      
      vec3 finalColor = mix(entropyColor, infoColor, vCoherence);
      
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      // Glow intensity tied to Information level
      gl_FragColor = vec4(finalColor * (0.8 + vCoherence), 0.7 + vCoherence * 0.3);
    }
  `
};

export default function QFCInformationCoherence({ frame }: { frame: any }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  
  const geometry = useMemo(() => {
    const count = 3000;
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      pos[i * 3] = Math.cos(theta);
      pos[i * 3 + 1] = Math.sin(theta);
      pos[i * 3 + 2] = 0;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    return geo;
  }, []);

  useFrame(({ clock }) => {
    if (!materialRef.current) return;
    const t = clock.getElapsedTime();
    materialRef.current.uniforms.uTime.value = t;
    
    // Convergence Logic matching the PASS status in the JSON
    // Smoothly transition to I_final = 0.95 over time
    const progress = Math.min(t / 8, 1.0); 
    const c_phi = progress * 0.953;
    const d_phi = 1.0 - c_phi;

    materialRef.current.uniforms.uCoherence.value = c_phi;
    materialRef.current.uniforms.uDispersion.value = d_phi;
  });

  return (
    <div className="w-full h-full bg-black flex flex-col items-center justify-center">
      <div className="absolute top-10 left-10 font-mono text-[10px] text-yellow-500 z-10 space-y-2 border-l border-yellow-900 pl-4">
        <p>SCENE: VOL4_COHERENCE_PHASE_LOCK</p>
        <p>LOCK_ID: VolIV-INFO-COHERENCE-v0.1</p>
        <p>IDENTITY: I = 1 - D_phi</p>
        <div className="pt-4 space-y-1">
          <p>METRICS_LIVE:</p>
          <p>C_phi (Coherence): {(0.953).toFixed(4)}</p>
          <p>D_phi (Dispersion): {(0.046).toFixed(4)}</p>
          <p className="text-white">I_final: PASS</p>
        </div>
      </div>

      <points geometry={geometry}>
        <shaderMaterial 
          ref={materialRef} 
          {...vol4CoherenceShader} 
          transparent 
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </points>

      <div className="absolute bottom-10 font-mono text-[9px] text-gray-600 uppercase tracking-widest">
        Entropy Decay → Information Emergence (ΔS &lt; 0 ⟹ ΔI &gt; 0)
      </div>
    </div>
  );
}