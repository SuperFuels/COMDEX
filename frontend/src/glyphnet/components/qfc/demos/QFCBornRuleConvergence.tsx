"use client";

import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html as DreiHtml } from "@react-three/drei";
import * as THREE from "three";

/**
 * PAEV-A3: BORN RULE CONVERGENCE
 * Logic: L1 Error minimization (Sampling vs. Theoretical)
 * Soul: Phase transition from Jittered Error to Deterministic Probability
 */

const bornRuleShader = {
  uniforms: {
    uTime: { value: 0 },
    uConvergence: { value: 0 }, // Progress toward exact Born heights [0..1]
    uBucketIndex: { value: 0 },
  },
  vertexShader: `
    varying float vCoherence;
    varying float vHeightFactor;
    varying vec2 vUv;
    
    uniform float uTime;
    uniform float uConvergence;
    uniform float uBucketIndex;

    void main() {
      vUv = uv;
      vec3 pos = position;

      // Deterministic Born Probability Heights (P_PA)
      float targets[5];
      targets[0] = 0.033; targets[1] = 0.262; targets[2] = 0.181;
      targets[3] = 0.098; targets[4] = 0.423;

      int bi = int(clamp(uBucketIndex, 0.0, 4.0));
      float targetHeight = targets[bi] * 18.0;

      // Sampling Noise: Oscillatory jitter that dampens as convergence hits 1.0
      float samplingNoise = sin(uTime * 15.0 + uBucketIndex) * 0.4 * (1.0 - uConvergence);
      
      // Scale from the bottom (base is at y=0 due to mesh translation in JSX)
      if (pos.y > 0.0) {
        pos.y = mix(0.1, targetHeight + samplingNoise, uConvergence);
      }

      vHeightFactor = pos.y / 18.0;
      vCoherence = uConvergence;
      
      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  fragmentShader: `
    varying float vCoherence;
    varying float vHeightFactor;
    varying vec2 vUv;

    void main() {
      // Color shift: Unstable Error (Red/Orange) -> Born Stability (Cyan/White)
      vec3 errorColor = vec3(0.9, 0.3, 0.2);
      vec3 bornColor  = vec3(0.0, 0.9, 0.8);
      vec3 stableWhite = vec3(1.0, 1.0, 1.0);

      vec3 base = mix(errorColor, bornColor, vCoherence);
      
      // Vertical gradient for "Density" feel
      vec3 finalColor = mix(base, stableWhite, vHeightFactor * vCoherence);

      // Subtle scanline effect
      float scanline = sin(vUv.y * 50.0 - vCoherence * 10.0) * 0.1;
      
      gl_FragColor = vec4(finalColor + scanline, 0.85);
    }
  `,
};

export default function QFCBornRuleConvergence({ frame }: { frame?: any }) {
  const matsRef = useRef<THREE.ShaderMaterial[]>([]);
  const [convergenceHUD, setConvergenceHUD] = useState(0);

  // Geometry: Shifted so 0,0,0 is at the bottom face for easy scaling
  const geometry = useMemo(() => {
    const geo = new THREE.BoxGeometry(1.5, 1, 0.5, 1, 20, 1);
    geo.translate(0, 0.5, 0); // Translate so bottom is at Y=0
    return geo;
  }, []);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    // Force a stable 0->1 cycle or follow external frame data
    const progress = frame?.convergence ?? (Math.sin(t * 0.4) * 0.5 + 0.5);

    matsRef.current.forEach((m, i) => {
      if (m) {
        m.uniforms.uTime.value = t;
        m.uniforms.uConvergence.value = progress;
        m.uniforms.uBucketIndex.value = i;
      }
    });

    if (Math.floor(t * 10) % 2 === 0) setConvergenceHUD(progress);
  });

  return (
    <group position={[0, -4, 0]}>
      <DreiHtml fullscreen transform={false} zIndexRange={[100, 0]}>
        <div className="pointer-events-none w-full h-full font-mono text-white">
          {/* Header Panel */}
          <div className="absolute top-10 left-10 p-5 bg-black/60 border border-emerald-500/20 backdrop-blur-md w-80">
            <div className="text-emerald-400 font-bold text-[10px] tracking-widest border-b border-emerald-500/20 pb-2 mb-4">
              PAEV-A3 // BORN_CONSISTENCY
            </div>
            <div className="space-y-3 text-[10px]">
              <div className="flex justify-between text-slate-400">
                <span>IDENTITY:</span>
                <span className="text-white">P_PA ≡ ||Π_i ψ||² / ||ψ||²</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>CONVERGENCE:</span>
                <span className="text-emerald-400 font-bold">{(convergenceHUD * 100).toFixed(1)}%</span>
              </div>
              <div className="h-1 w-full bg-emerald-900/40 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-emerald-400 shadow-[0_0_10px_#4ade80]" 
                  style={{ width: `${convergenceHUD * 100}%` }} 
                />
              </div>
            </div>
          </div>

          {/* Bottom Error Logs */}
          <div className="absolute top-10 right-10 text-right p-5 bg-black/60 border border-emerald-500/20 backdrop-blur-md">
            <div className="text-[9px] text-slate-500 uppercase tracking-tighter mb-2">Sampling Audit (L-Norms)</div>
            <div className="space-y-1 text-[10px]">
              <p className="text-slate-400">L1_ERROR: <span className="text-white">{(8.26e-6 * (1 - convergenceHUD + 0.01)).toExponential(2)}</span></p>
              <p className="text-slate-400">L_INF: <span className="text-white">{(4.05e-6 * (1 - convergenceHUD + 0.01)).toExponential(2)}</span></p>
            </div>
          </div>

          <div className="absolute bottom-10 left-1/2 -translate-x-1/2 text-[9px] text-slate-600 tracking-[0.4em] uppercase">
            Projector Validation • N=5 • K=100k
          </div>
        </div>
      </DreiHtml>

      {/* Probability Bars */}
      {Array.from({ length: 5 }).map((_, i) => (
        <group key={i} position={[(i - 2) * 2.5, 0, 0]}>
          {/* Main Solid Bar */}
          <mesh geometry={geometry}>
            <shaderMaterial
              ref={(m) => {
                if (m) matsRef.current[i] = m as THREE.ShaderMaterial;
              }}
              {...bornRuleShader}
              transparent
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </mesh>
          
          {/* Ghost Ideal (Wireframe showing the target height) */}
          <mesh geometry={geometry} scale={[1.05, 1, 1.05]}>
            <meshBasicMaterial 
              color="#00ffcc" 
              wireframe 
              transparent 
              opacity={0.05 + (convergenceHUD * 0.1)} 
            />
          </mesh>
        </group>
      ))}

      <ambientLight intensity={0.2} />
      <pointLight position={[0, 10, 5]} intensity={1} color="#4ade80" />
    </group>
  );
}