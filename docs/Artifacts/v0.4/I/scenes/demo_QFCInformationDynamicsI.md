"use client";
import React, { useRef, useState, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

/** * PINNED ARTIFACTS: RUN_ID I20251231T003433Z_I
 * Source: docs/Artifacts/v0.4/I/runs/I20251231T003433Z_I/
 */
const PINNED_I_METRICS = {
  vs_vc_ratio: 18.02,     // I3 Boost Invariance
  rho_burst: -0.013,      // I5c Inconclusive Correlation
  p_val: 0.248,           // I5c Significance
  best_lag: 0.10,         // I5c Best Lag (seconds)
  alpha_transport: 0.39,  // I1 Mean Exponent
};

const InformationFront = () => {
  const meshRef = useRef<THREE.Group>(null!);
  
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    // V_c expansion (Causal)
    const r_c = (t % 5) * 2; 
    // V_s expansion (Entropic Proxy - 18x faster/ahead)
    const r_s = r_c * 1.5; // Scaled for viewport visibility
    
    meshRef.current.children[0].scale.setScalar(r_c); // Causal Ring
    meshRef.current.children[1].scale.setScalar(r_s); // Entropic Halo
    meshRef.current.children[1].opacity = 0.2 + Math.sin(t * 10) * 0.1;
  });

  return (
    <group ref={meshRef}>
      {/* Causal Bound */}
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.98, 1, 64]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={0.8} />
      </mesh>
      {/* Entropic Leak (vS proxy) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.1, 1.3, 64]} />
        <meshBasicMaterial color="#00f2ff" transparent opacity={0.3} />
      </mesh>
    </group>
  );
};

export default function QFCInformationDynamicsI() {
  const [burstActive, setBurstActive] = useState(false);

  return (
    <div className="w-full h-screen bg-black text-cyan-400 font-mono flex">
      <div className="w-3/4 relative border-r border-slate-800">
        <Canvas camera={{ position: [0, 10, 0], fov: 50 }}>
          <gridHelper args={[20, 40, 0x112233, 0x050505]} />
          <InformationFront />
        </Canvas>

        {/* HUD OVERLAY */}
        <div className="absolute top-10 left-10 space-y-4 bg-black/60 p-6 border border-cyan-900/50 backdrop-blur-sm">
          <h1 className="text-xl font-bold tracking-tighter">I-SERIES: SIGNAL_PROPAGATION</h1>
          <div className="text-[10px] space-y-1">
            <p>RUN_ID: <span className="text-white">I20251231T003433Z_I</span></p>
            <p>TRANSPORT: <span className="text-white">DIFFUSIVE-DOMINANT (α ≈ {PINNED_I_METRICS.alpha_transport})</span></p>
            <p>RATIO (vS/vc): <span className="text-white">{PINNED_I_METRICS.vs_vc_ratio} (Boost Invariant)</span></p>
          </div>
        </div>
      </div>

      <div className="w-1/4 p-8 flex flex-col justify-between bg-[#05050a]">
        <div className="space-y-8">
          <section>
            <h3 className="text-xs uppercase text-slate-500 mb-2">Burst Analysis (I5c)</h3>
            <div className={`p-4 border ${burstActive ? 'border-yellow-500 bg-yellow-500/10' : 'border-slate-800'}`}>
              <p className="text-[10px]">CORRELATION (ρ): {PINNED_I_METRICS.rho_burst.toFixed(3)}</p>
              <p className="text-[10px] text-red-500">SIGNIFICANCE (p): {PINNED_I_METRICS.p_val.toFixed(3)}</p>
              <div className="mt-4 text-xs font-bold text-center">
                {PINNED_I_METRICS.p_val > 0.05 ? "INCONCLUSIVE COUPLING" : "COUPLING DETECTED"}
              </div>
            </div>
          </section>
        </div>
        
        <div className="text-[9px] text-slate-600 leading-tight">
          Disclaimer: Visualizations are model-scoped algebraic proxies. No physical superluminal signalling is claimed.
        </div>
      </div>
    </div>
  );
}