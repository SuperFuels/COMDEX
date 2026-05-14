"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";

/**
 * VOL-M: EMERGENT METRIC GEOMETRY
 * Logic: Metric Tensor g_uv + Redshift coupling
 * Soul: Coupled Curvature Wells & Beat Frequency Resonance
 */

const mSeriesShader = {
  uniforms: {
    uTime: { value: 0 },
    uGtt: { value: -1.122 },
    uGxx: { value: 1.027 },
    uCentroidPos: { value: new THREE.Vector2(0, 0) },
    uBeatFrequency: { value: 0.02083 }, 
    uTransferAmplitude: { value: 0.002392 }, 
    uRedshift: { value: 0 },
    uBrightness: { value: 1.0 },
  },
  vertexShader: `
    varying float vIntensity;
    varying float vRedshiftFactor;
    varying vec3 vViewPosition;
    varying vec3 vWorldPosition;

    uniform float uTime;
    uniform float uBeatFrequency;
    uniform float uTransferAmplitude;
    uniform vec2 uCentroidPos;
    uniform float uRedshift;

    void main() {
      vec3 pos = position;

      // M4b: Well Interaction (Dual Harmonic Oscillators)
      float wellA = exp(-pow(pos.x + 20.0, 2.0) / 100.0);
      float wellB = exp(-pow(pos.x - 20.0, 2.0) / 100.0);
      
      // Energy exchange between wells at Beat Frequency
      float exchange = sin(uTime * uBeatFrequency * 10.0) * uTransferAmplitude * 400.0;
      float warping = (wellA - wellB) * exchange;

      // M3d: Centroid Geodesic influence
      float distToCentroid = length(pos.xy - uCentroidPos);
      float centroidWell = exp(-pow(distToCentroid, 2.0) / 40.0) * 2.5;

      // Cumulative Metric Deformation
      pos.z += warping + (centroidWell * sin(uTime * 0.5));
      
      // Metric Contraction (Visual scaling toward wells)
      float contraction = 1.0 + (warping * 0.1);
      pos.xy *= contraction;

      vIntensity = abs(warping) + centroidWell;
      vRedshiftFactor = uRedshift * 1000.0;

      vec4 worldPos = modelMatrix * vec4(pos, 1.0);
      vWorldPosition = worldPos.xyz;
      vec4 mvPosition = viewMatrix * worldPos;
      vViewPosition = -mvPosition.xyz;

      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  fragmentShader: `
    varying float vIntensity;
    varying float vRedshiftFactor;
    varying vec3 vWorldPosition;
    varying vec3 vViewPosition;
    
    uniform float uBrightness;

    void main() {
      // GRID LOGIC
      vec2 grid = abs(fract(vWorldPosition.xy * 0.2) - 0.5) / fwidth(vWorldPosition.xy * 0.2);
      float line = 1.0 - min(grid.x, grid.y);
      line = smoothstep(0.0, 1.0, line);

      // PALETTE: Void Navy -> Metric Teal -> Shift Amber
      vec3 navy = vec3(0.02, 0.05, 0.12);
      vec3 teal = vec3(0.0, 0.6, 0.8);
      vec3 amber = vec3(1.0, 0.4, 0.1);

      // Color base shifts with metric intensity
      vec3 base = mix(navy, teal, clamp(vIntensity * 0.3, 0.0, 1.0));
      
      // Apply Redshift tinting (M5)
      vec3 shiftColor = mix(base, amber, clamp(abs(vRedshiftFactor), 0.0, 0.6));
      
      // Grid illumination
      vec3 finalColor = mix(shiftColor, shiftColor * 3.0, line * 0.4);

      // Fresnel glow for the "curvature ripples"
      vec3 viewDir = normalize(vViewPosition);
      float fresnel = pow(1.0 - max(0.0, dot(vec3(0,0,1), viewDir)), 3.0);

      float alpha = 0.85 + (fresnel * 0.15);
      gl_FragColor = vec4(finalColor * uBrightness, alpha);
    }
  `,
};

export default function QFCEmergentGeometryM_V2() {
  const meshRef = useRef<THREE.Mesh>(null!);
  const [hudData, setHudData] = useState({ rs: -5.889e-6, centroid: 0 });

  const geometry = useMemo(() => new THREE.PlaneGeometry(120, 60, 128, 64), []);
  const uniforms = useMemo(() => THREE.UniformsUtils.clone(mSeriesShader.uniforms), []);
  const tRef = useRef(0);

  useFrame((_state, dtRaw) => {
    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;
    const t = tRef.current;

    uniforms.uTime.value = t;

    // Centroid motion (M3d)
    const cX = Math.sin(t * 0.5) * 5.852;
    uniforms.uCentroidPos.value.set(cX, 0);

    // Redshift oscillation (M5)
    const currentRS = -5.889e-6 * (1 + Math.sin(t * 0.7) * 0.5);
    uniforms.uRedshift.value = currentRS;
    uniforms.uBrightness.value = 0.95 + 0.05 * Math.sin(t * 1.2);

    if (t % 0.1 < 0.02) setHudData({ rs: currentRS, centroid: cX });
  });

  return (
    <group>
      <Html fullscreen transform={false} zIndexRange={[100, 0]}>
        <div className="pointer-events-none w-full h-full font-mono text-white p-8">
          <div className="absolute top-10 left-10 p-6 bg-black/40 backdrop-blur-xl border border-white/5 rounded-lg w-80 shadow-2xl">
            <div className="text-purple-400 text-[10px] tracking-[0.4em] font-bold border-b border-purple-500/20 pb-2 mb-4">
              M_SERIES: METRIC_WELLS
            </div>
            
            <div className="space-y-4 text-[10px]">
              <div className="flex justify-between text-slate-400">
                <span>g_tt / g_xx RATIO:</span>
                <span className="text-white">1.092</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>REDSHIFT (Δω/ω):</span>
                <span className="text-orange-400 font-bold">{hudData.rs.toExponential(3)}</span>
              </div>
              <div className="h-0.5 w-full bg-white/5"><div className="h-full bg-purple-500" style={{ width: '65%' }} /></div>
              <div className="flex justify-between text-[9px] opacity-50 italic">
                <span>CENTROID_X:</span>
                <span>{hudData.centroid.toFixed(3)}</span>
              </div>
            </div>
          </div>
        </div>
      </Html>

      <mesh ref={meshRef} geometry={geometry} rotation={[-Math.PI / 2.5, 0, 0]} position={[0, -2, -10]}>
        <shaderMaterial
          {...mSeriesShader}
          uniforms={uniforms}
          transparent
          side={THREE.DoubleSide}
          wireframe={false}
        />
      </mesh>

      {/* Well Markers */}
      <group position={[0, -5, -10]}>
        <WellMarker position={[-20, 0, 0]} color="#4a00ff" />
        <WellMarker position={[20, 0, 0]} color="#4a00ff" />
      </group>

      <pointLight position={[0, 10, 0]} intensity={2} color="#00d2ff" distance={50} />
      <ambientLight intensity={0.2} />
    </group>
  );
}

function WellMarker({ position, color }: { position: [number, number, number], color: string }) {
  return (
    <mesh position={position}>
      <cylinderGeometry args={[0.5, 0.5, 20, 16]} />
      <meshStandardMaterial color={color} transparent opacity={0.1} emissive={color} emissiveIntensity={2} />
    </mesh>
  );
}