import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

export default function QFCDemoGravity({ frame }: { frame: any }) {
  const meshRef = useRef<THREE.Points>(null);
  const coreRef = useRef<THREE.Mesh>(null);

  // High-density lattice for metric distortion
  const { points, originalY } = useMemo(() => {
    const size = 20;
    const res = 80;
    const p = new Float32Array(res * res * 3);
    const yOrig = new Float32Array(res * res);
    for (let i = 0; i < res; i++) {
      for (let j = 0; j < res; j++) {
        const x = (i / res - 0.5) * size;
        const z = (j / res - 0.5) * size;
        p[(i * res + j) * 3 + 0] = x;
        p[(i * res + j) * 3 + 1] = 0; // Start flat
        p[(i * res + j) * 3 + 2] = z;
        yOrig[i * res + j] = 0;
      }
    }
    return { points: p, originalY: yOrig };
  }, []);

  useFrame(({ clock }) => {
    if (!meshRef.current || !coreRef.current) return;
    const t = clock.getElapsedTime();
    
    // Telemetry Mapping
    const kappa = frame?.kappa ?? 0.25;
    const curv = frame?.curv ?? 0.18;
    const alpha = frame?.alpha ?? 0.12;

    const posAttr = meshRef.current.geometry.attributes.position.array as Float32Array;
    
    // Core dynamics: "The Pulsing Singularity"
    const pulse = 1.0 + 0.15 * Math.sin(t * (1.5 + alpha * 2.0));
    coreRef.current.scale.setScalar(pulse * (0.8 + curv * 1.5));
    coreRef.current.rotation.y = t * 0.5;

    // Metric Displacement Logic (Lorentzian Warp)
    for (let i = 0; i < originalY.length; i++) {
      const px = posAttr[i * 3 + 0];
      const pz = posAttr[i * 3 + 2];
      const dist = Math.sqrt(px * px + pz * pz);

      // G-Series Metric: y = - (Depth / (1 + Dist^2))
      // Curv deepens the well; Kappa tightens the radius
      const depth = (curv * 6.0) + (kappa * 2.0);
      const tightness = 1.0 + (kappa * 4.0);
      const displacement = - (depth / (1.0 + Math.pow(dist / tightness, 2.0)));
      
      // Subtle background "Gravitational Waves"
      const waves = Math.sin(dist * 1.2 - t * 2.5) * 0.08 * alpha;
      
      posAttr[i * 3 + 1] = displacement + waves;
    }
    
    meshRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <group position={[0, 1.5, 0]}>
      {/* The Central Mass (Causal Core) */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[1, 64, 64]} />
        <meshStandardMaterial
          color={"#0ea5e9"}
          emissive={"#38bdf8"}
          emissiveIntensity={2.0}
          roughness={0.1}
          metalness={0.9}
        />
        <pointLight intensity={2.5} distance={15} color="#38bdf8" />
      </mesh>

      {/* The Warped Spacetime Lattice */}
      <points ref={meshRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={points.length / 3}
            array={points}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial 
          size={0.06} 
          color="#94a3b8" 
          transparent 
          opacity={0.4} 
          blending={THREE.AdditiveBlending}
        />
      </points>

      {/* Event Horizon Glow */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]}>
        <ringGeometry args={[0.5, 6, 64]} />
        <meshBasicMaterial color="#0ea5e9" transparent opacity={0.05} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}