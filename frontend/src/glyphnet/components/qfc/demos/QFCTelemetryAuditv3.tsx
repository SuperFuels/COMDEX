"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html as DreiHtml } from "@react-three/drei";
import * as THREE from "three";

/**
 * VOL-5: TELEMETRY AUDIT (Upgraded)
 * Logic: Trace Replay / Deterministic Flow
 * Soul: Digital Osmosis / Stream-Packet Lattice
 */

const telemetryAuditShader = {
  uniforms: {
    uTime: { value: 0 },
    uFinalCoherence: { value: 0.9463 },
    uVerified: { value: 1.0 },
    uBrightness: { value: 1.0 },
  },
  vertexShader: `
    varying float vAlpha;
    varying float vLane;
    varying float vIntensity;

    uniform float uTime;
    uniform float uFinalCoherence;

    void main() {
      vec3 pos = position;

      // Lane indexing (0..3)
      float lane = floor((pos.y + 3.3) / 2.2 + 0.001);
      vLane = lane;

      // Stream velocity influenced by coherence
      float speed = 2.5 + (uFinalCoherence * 1.5);
      float x = mod(pos.x + uTime * speed + (lane * 2.0), 20.0) - 10.0;
      pos.x = x;

      // Localized turbulence: dissipates as coherence rises
      float noise = sin(x * 2.0 + uTime * 3.0 + lane) * (1.0 - uFinalCoherence) * 0.4;
      pos.y += noise;
      pos.z += cos(x * 1.5 + uTime) * 0.1;

      // Head-to-tail intensity mapping
      // Points are brighter at the leading edge of the wrap
      float head = smoothstep(-10.0, 8.0, x);
      vIntensity = pow(head, 2.0);

      // Edge fading for seamless wrap
      vAlpha = smoothstep(-10.0, -8.0, x) * (1.0 - smoothstep(8.5, 10.0, x));

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;

      // Points grow as they "process" (move right)
      gl_PointSize = (1.5 + 2.5 * vIntensity) * (0.8 + 0.2 * uFinalCoherence);
    }
  `,
  fragmentShader: `
    varying float vAlpha;
    varying float vLane;
    varying float vIntensity;

    uniform float uFinalCoherence;
    uniform float uVerified;
    uniform float uBrightness;

    void main() {
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      // PALETTE: Void Violet -> Stream Cyan -> Verified White
      vec3 violet = vec3(0.40, 0.15, 1.00);
      vec3 cyan   = vec3(0.00, 0.85, 1.00);
      vec3 white  = vec3(0.95, 0.95, 1.00);

      // Base color moves from Violet to Cyan based on lane and overall coherence
      vec3 laneBase = mix(violet, cyan, (vLane / 3.0) * uFinalCoherence);
      
      // Verification "locks" the color to the Bridge-White
      vec3 finalColor = mix(laneBase, white, uVerified * vIntensity * 0.6);

      float glow = vIntensity * 0.4 * uBrightness;
      float alpha = vAlpha * (0.3 + 0.6 * uFinalCoherence);

      gl_FragColor = vec4(finalColor * (0.8 + glow), alpha);
    }
  `,
};

export default function QFCTelemetryAuditV4({ frame }: { frame?: any }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const tRef = useRef(0);

  // Increased density: 8 lanes, 60 steps for a more "continuous" data feel
  const geometry = useMemo(() => {
    const lanes = 8;
    const steps = 60;
    const pts = new Float32Array(lanes * steps * 3);

    let k = 0;
    for (let lane = 0; lane < lanes; lane++) {
      for (let i = 0; i < steps; i++) {
        pts[k++] = (i / steps) * 20 - 10;
        pts[k++] = (lane - (lanes-1)/2) * 1.2;
        pts[k++] = 0;
      }
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pts, 3));
    return geo;
  }, []);

  useEffect(() => () => geometry.dispose(), [geometry]);

  useFrame((_state, dtRaw) => {
    const mat = materialRef.current;
    if (!mat) return;

    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;
    mat.uniforms.uTime.value = tRef.current;

    // Smooth transition for plumbing
    const targetC = frame?.c_final ?? 0.9463;
    mat.uniforms.uFinalCoherence.value = THREE.MathUtils.lerp(
      mat.uniforms.uFinalCoherence.value,
      targetC,
      0.05
    );

    mat.uniforms.uVerified.value = frame?.verified === false ? 0.0 : 1.0;
    mat.uniforms.uBrightness.value = 1.0 + 0.05 * Math.sin(tRef.current * 1.2);
  });

  return (
    <group rotation={[Math.PI / 12, 0, 0]}>
      <DreiHtml fullscreen transform={false} zIndexRange={[100, 0]}>
        <div className="pointer-events-none w-full h-full font-mono text-white">
          {/* Top Info Bar */}
          <div className="absolute top-8 left-8 flex items-center gap-6 pointer-events-auto bg-black/40 backdrop-blur-md p-4 border border-white/10 rounded">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-cyan-400 rounded-sm shadow-[0_0_8px_cyan] animate-pulse" />
              <span className="text-[11px] font-bold tracking-[0.2em]">AUDIT_V5: DETERMINISM</span>
            </div>
            <div className="h-4 w-px bg-white/20" />
            <div className="text-[9px] text-slate-400">
              STATUS: <span className="text-cyan-300 uppercase">Verification_Pass</span>
            </div>
          </div>

          {/* Metric Stack */}
          <div className="absolute top-8 right-8 text-right space-y-4 pointer-events-auto">
            <div className="bg-black/40 backdrop-blur-md p-4 border border-white/10 rounded w-48">
              <div className="text-[8px] text-slate-500 mb-1 tracking-widest uppercase">Coherence Metric</div>
              <div className="text-xl font-light text-cyan-200">0.94630</div>
              <div className="mt-2 h-0.5 w-full bg-white/10">
                <div className="h-full bg-cyan-500" style={{ width: '94.6%' }} />
              </div>
            </div>
            <div className="text-[9px] text-slate-500 space-y-1 pr-2">
              <p>TRACE_INDEX: 0x67B3...6218</p>
              <p>BUFFER_HEALTH: 100%</p>
            </div>
          </div>

          <div className="absolute bottom-10 left-1/2 -translate-x-1/2 text-[9px] text-slate-500 tracking-[0.4em] uppercase opacity-50">
            Causal Trace Replay • System Deterministic
          </div>
        </div>
      </DreiHtml>

      <points geometry={geometry}>
        <shaderMaterial
          ref={materialRef}
          {...telemetryAuditShader}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </points>

      {/* Internal "Data Core" light flow */}
      <rectAreaLight
        width={20}
        height={1}
        intensity={2}
        color="#00f2ff"
        position={[0, 0, -1]}
      />
    </group>
  );
}