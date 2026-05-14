"use client";

import React, { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html as DreiHtml } from "@react-three/drei";
import * as THREE from "three";

/**
 * VOL-I: INFORMATION DYNAMICS / SIGNAL PROPAGATION
 * Logic: Causal vs Entropic Velocity (vS/vC ratio)
 * Soul: Light-Cone Propagation / Information Diffusion
 */

const PINNED_I_METRICS = {
  vs_vc_ratio: 18.02,
  rho_burst: -0.013,
  p_val: 0.248,
  best_lag: 0.10,
  alpha_transport: 0.39,
};

const SignalShader = {
  uniforms: {
    uTime: { value: 0 },
    uAlpha: { value: 0.39 },
    uRatio: { value: 1.55 },
    uColor: { value: new THREE.Color("#00d2ff") },
  },
  vertexShader: `
    varying float vIntensity;
    varying float vDistance;
    uniform float uTime;
    uniform float uAlpha;

    void main() {
      vec3 pos = position;
      float d = length(pos.xy);
      
      // Signal Propagation Logic: Expansion + Alpha Diffusion
      // r(t) = t^alpha
      float cycle = mod(uTime * 0.8, 5.0);
      float front = pow(cycle, 1.0 + uAlpha * 0.5);
      
      // Wave pulse height
      float wave = exp(-pow(d - front, 2.0) / (0.1 + uAlpha));
      pos.z += wave * 1.5;

      vIntensity = wave;
      vDistance = d;

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;
      gl_PointSize = 2.0 * (1.0 + wave * 2.0);
    }
  `,
  fragmentShader: `
    varying float vIntensity;
    varying float vDistance;
    uniform vec3 uColor;

    void main() {
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      // Causal Front (White) vs Entropic Echo (Cyan/Violet)
      vec3 frontColor = vec3(1.0, 1.0, 1.0);
      vec3 echoColor = uColor;

      vec3 finalColor = mix(echoColor, frontColor, pow(vIntensity, 2.0));
      
      // Fade out based on distance from the origin
      float edgeFade = 1.0 - smoothstep(4.0, 6.0, vDistance);
      
      gl_FragColor = vec4(finalColor * (0.5 + vIntensity), vIntensity * edgeFade);
    }
  `,
};

export default function QFCInformationDynamicsI({ frame }: { frame?: any }) {
  const pointsRef = useRef<THREE.Points>(null!);
  const tRef = useRef(0);
  const [hudTick, setHudTick] = useState(0);

  // Pull metrics or defaults
  const alpha = frame?.i_alpha_transport ?? PINNED_I_METRICS.alpha_transport;
  const vsVc = frame?.i_vs_vc_ratio ?? PINNED_I_METRICS.vs_vc_ratio;

  // Geometry: A high-density radial grid
  const geometry = useMemo(() => {
    const pts = [];
    const count = 120;
    for (let i = 0; i < count; i++) {
      for (let j = 0; j < count; j++) {
        const angle = (i / count) * Math.PI * 2;
        const radius = (j / count) * 6;
        pts.push(Math.cos(angle) * radius, Math.sin(angle) * radius, 0);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    return geo;
  }, []);

  useFrame((_state, dtRaw) => {
    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;
    
    if (pointsRef.current) {
      const mat = pointsRef.current.material as THREE.ShaderMaterial;
      mat.uniforms.uTime.value = tRef.current;
      mat.uniforms.uAlpha.value = alpha;
    }

    if (tRef.current % 0.2 < 0.02) setHudTick(tRef.current);
  });

  return (
    <group position={[0, -0.5, 0]}>
      <DreiHtml fullscreen transform={false}>
        <div className="pointer-events-none w-full h-full font-mono text-white p-10">
          {/* Diagnostic Sidebar */}
          <div className="absolute top-10 left-10 w-80 p-6 bg-black/60 backdrop-blur-xl border border-white/5 rounded-sm">
            <h2 className="text-[10px] tracking-[0.4em] text-cyan-400 font-bold mb-6 border-b border-white/10 pb-2">
              SIGNAL_PROPAGATION_I
            </h2>
            
            <div className="space-y-4">
              <div className="space-y-1">
                <div className="flex justify-between text-[10px]">
                  <span className="text-slate-500 uppercase">Transport Exponent (α)</span>
                  <span className="text-white">{alpha.toFixed(3)}</span>
                </div>
                <div className="h-0.5 w-full bg-white/5">
                  <div className="h-full bg-cyan-500 shadow-[0_0_8px_cyan]" style={{ width: `${alpha * 100}%` }} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="bg-white/5 p-3">
                  <span className="block text-[8px] text-slate-500 uppercase">Ratio vS/vC</span>
                  <span className="text-sm text-white font-light">{vsVc.toFixed(2)}</span>
                </div>
                <div className="bg-white/5 p-3">
                  <span className="block text-[8px] text-slate-500 uppercase">Lag Index</span>
                  <span className="text-sm text-white font-light">{PINNED_I_METRICS.best_lag}s</span>
                </div>
              </div>

              <div className="pt-4 border-t border-white/5">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                  <span className="text-[9px] text-slate-400 tracking-widest uppercase italic">
                    {alpha > 0.5 ? "Ballistic Propagation" : "Diffusive Dominated"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </DreiHtml>

      {/* Ground Reference Grid */}
      <gridHelper args={[20, 40, 0x112233, 0x05060a]} rotation={[Math.PI / 2, 0, 0]} />

      {/* Information Propagation Points */}
      <points ref={pointsRef} rotation={[-Math.PI / 2, 0, 0]} geometry={geometry}>
        <shaderMaterial
          {...SignalShader}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </points>

      {/* Ambient Source Glow */}
      <pointLight position={[0, 1, 0]} intensity={1.5} color="#00f2ff" distance={10} />
    </group>
  );
}