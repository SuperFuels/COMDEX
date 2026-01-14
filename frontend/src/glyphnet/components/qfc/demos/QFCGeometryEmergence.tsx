"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";

/**
 * VOL-VII: N-CORE EMERGENCE
 * Logic: Stochastic Chaos ↔ Phase-Locked Ring
 * Soul: Orbital Mechanics / Topological Closure
 */

const emergenceShader = {
  uniforms: {
    uTime: { value: 0 },
    uMode: { value: 0 },
    uNoiseSigma: { value: 0.0 },
    uClosureRatio: { value: 1.0 },
    uBrightness: { value: 1.0 },
    uRingR: { value: 4.5 },
    uSpin: { value: 0.12 },
  },
  vertexShader: `
    varying float vDistance;
    varying float vShell;
    varying float vTheta;
    varying float vClosure;
    varying float vId;

    uniform float uTime;
    uniform float uMode;
    uniform float uNoiseSigma;
    uniform float uClosureRatio;
    uniform float uRingR;
    uniform float uSpin;

    float rand(vec2 co){
      return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
    }

    void main() {
      vId = position.z;
      float id = vId;

      // CHAOS STATE: Spherical distribution
      float t = uTime * 0.5;
      vec3 chaos = vec3(
        sin(id * 0.12 + t) * 4.0,
        cos(id * 0.08 + t * 0.9) * 4.0,
        sin(id * 0.15 + t * 0.5) * 3.0
      );

      // Noise Injection (N6/N7)
      if (uMode == 1.0) {
        chaos += (rand(vec2(id, uTime)) - 0.5) * uNoiseSigma * 15.0;
      }

      // TARGET RING: Phase-Locked Geometry
      float N = 400.0;
      float angle0 = (id / N) * 6.283185; 
      float angle = angle0 + (uTime * uSpin);
      
      // Radial breathing
      float r = uRingR + sin(uTime * 1.2 + angle0 * 4.0) * 0.15 * uClosureRatio;
      vec3 ring = vec3(cos(angle) * r, sin(angle) * r, sin(angle * 2.0 + uTime) * 0.2);

      // Backreaction Runaway (N9)
      if (uMode == 4.0) {
        float runaway = 1.0 + pow(sin(uTime * 0.3) * 0.5 + 0.5, 3.0) * 2.0;
        ring *= runaway;
        chaos *= runaway;
      }

      // Interpolate based on Closure
      vClosure = clamp(uClosureRatio, 0.0, 1.0);
      vec3 finalPos = mix(chaos, ring, vClosure);

      vDistance = length(finalPos.xy);
      vTheta = angle;
      
      // Intensity based on proximity to the target ring shell
      vShell = exp(-pow(vDistance - uRingR, 2.0) / 0.8);

      vec4 mvPosition = modelViewMatrix * vec4(finalPos, 1.0);
      gl_Position = projectionMatrix * mvPosition;

      // Particle size logic
      gl_PointSize = (2.0 + 3.0 * vClosure) * (0.8 + 0.2 * vShell);
    }
  `,
  fragmentShader: `
    varying float vDistance;
    varying float vShell;
    varying float vTheta;
    varying float vClosure;
    varying float vId;

    uniform float uMode;
    uniform float uBrightness;

    void main() {
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      // Palette
      vec3 violet = vec3(0.4, 0.15, 1.0);
      vec3 cyan   = vec3(0.0, 0.85, 1.0);
      vec3 white  = vec3(0.9, 0.9, 1.0);

      // Base color based on mode and closure
      vec3 base = mix(violet * 0.6, cyan, vClosure);
      
      // Azimuthal "Ticks" (The Ring Signature)
      float ticks = smoothstep(0.92, 1.0, cos(vTheta * 12.0 + vId));
      
      // Final composition
      vec3 color = mix(base, white, vShell * 0.5 + ticks * 0.5 * vClosure);

      if (uMode == 3.0) color = mix(color, vec3(1.0, 0.4, 0.2), 0.3); // Thermal

      float glow = (vShell * 0.5 + ticks * 0.2) * uBrightness;
      float alpha = clamp(0.2 + vClosure * 0.5 + glow, 0.0, 0.9);

      gl_FragColor = vec4(color * (0.8 + glow), alpha);
    }
  `,
};

type ModeKey = "STABLE" | "NOISE" | "ECHO" | "REPHASE" | "RUNAWAY";

export default function QFCGeometryEmergenceV3() {
  const [mode, setMode] = useState<ModeKey>("STABLE");
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const tRef = useRef(0);

  const modes = useMemo(() => ({
    STABLE: { id: 0, sigma: 0.0, closure: 1.0, label: "Unified Equilibrium" },
    NOISE: { id: 1, sigma: 0.12, closure: 0.6, label: "Noise Robustness" },
    ECHO: { id: 2, sigma: 0.0, closure: 0.4, label: "Echo Recovery" },
    REPHASE: { id: 3, sigma: 0.0, closure: 0.9, label: "Thermal Rephase" },
    RUNAWAY: { id: 4, sigma: 0.8, closure: 0.15, label: "Backreaction Runaway" },
  }), []);

  const geometry = useMemo(() => {
    const pts = new Float32Array(600 * 3); // Increased density
    for (let i = 0; i < 600; i++) {
      pts[i * 3 + 2] = i; 
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pts, 3));
    return geo;
  }, []);

  useFrame((_state, dtRaw) => {
    if (!materialRef.current) return;
    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;
    const mat = materialRef.current;
    const cfg = modes[mode];

    mat.uniforms.uTime.value = tRef.current;
    mat.uniforms.uMode.value = cfg.id;
    mat.uniforms.uNoiseSigma.value = cfg.sigma;
    mat.uniforms.uClosureRatio.value = THREE.MathUtils.lerp(mat.uniforms.uClosureRatio.value, cfg.closure, 0.08);
    mat.uniforms.uBrightness.value = 1.0 + 0.1 * Math.sin(tRef.current * 1.5);
  });

  return (
    <group>
      <Html fullscreen transform={false}>
        <div className="pointer-events-none w-full h-full font-mono text-white p-10">
          {/* Dashboard */}
          <div className="absolute top-10 left-10 w-72 p-6 bg-black/60 backdrop-blur-2xl border border-white/10 rounded-lg shadow-2xl">
            <div className="text-[10px] tracking-[0.4em] text-cyan-400 font-bold mb-6 border-b border-cyan-500/30 pb-2">
              VOL-VII: N_CORE_EMERGENCE
            </div>
            
            <div className="space-y-4 mb-8">
              <div className="flex justify-between text-[10px]">
                <span className="text-slate-500">MODE:</span>
                <span className="text-cyan-300 uppercase">{modes[mode].label}</span>
              </div>
              <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-cyan-500 transition-all duration-700" 
                  style={{ width: `${modes[mode].closure * 100}%` }}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {(Object.keys(modes) as ModeKey[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`pointer-events-auto py-2 text-[8px] tracking-widest border transition-all ${
                    mode === m ? "bg-cyan-500 text-black border-cyan-400" : "bg-transparent border-white/10 text-white hover:bg-white/5"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Html>

      <points geometry={geometry}>
        <shaderMaterial
          ref={materialRef}
          {...emergenceShader}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </points>

      {/* Volumetric Center Light */}
      <pointLight position={[0, 0, 2]} intensity={0.8} color="#00e5ff" />
      <ambientLight intensity={0.1} />
    </group>
  );
}