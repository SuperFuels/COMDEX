import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

export default function QFCDemoTunnel({ frame }: { frame: any }) {
  const meshRef = useRef<THREE.Points>(null);

  // Causal Constants
  const BARRIER_Z = -5.0;
  const BARRIER_WIDTH = 2.5;

  const { points, colors } = useMemo(() => {
    const COUNT = 4500; // Increased density for reflection detail
    const p = new Float32Array(COUNT * 3);
    const c = new Float32Array(COUNT * 3);
    for (let i = 0; i < COUNT; i++) {
      p[i * 3 + 0] = (Math.random() - 0.5) * 4.5;
      p[i * 3 + 1] = (Math.random() - 0.5) * 4.5;
      p[i * 3 + 2] = (Math.random() - 0.5) * 36 - 18;
    }
    return { points: p, colors: c };
  }, []);

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const t = clock.getElapsedTime() * 2.5;
    const sigma = frame?.sigma ?? 0.5;
    const alpha = frame?.alpha ?? 0.2;
    
    const posAttr = meshRef.current.geometry.attributes.position.array as Float32Array;
    const colAttr = meshRef.current.geometry.attributes.color.array as Float32Array;

    for (let i = 0; i < points.length / 3; i++) {
      const x = points[i * 3 + 0];
      const y = points[i * 3 + 1];
      const z = points[i * 3 + 2];

      // 1. INCIDENT WAVE (Moving Forward)
      const v = (2.0 + sigma * 4.0);
      const centerIn = ((t * v) % 44) - 22;
      const pulseIn = Math.exp(-Math.pow(z - centerIn, 2.0) / 1.5);

      // 2. REFLECTED WAVE (Moving Backward from Barrier)
      // Logic: Starts at barrier, moves +Z (backward)
      const reflectionStart = BARRIER_Z;
      const centerRefl = reflectionStart + (t * v % 44); 
      const pulseRefl = Math.exp(-Math.pow(z - centerRefl, 2.0) / 1.5) * (1.0 - alpha);

      // 3. BARRIER LOGIC
      const inBarrier = z > BARRIER_Z && z < BARRIER_Z + BARRIER_WIDTH;
      const pastBarrier = z >= BARRIER_Z + BARRIER_WIDTH;

      let intensity = 0;
      let r=1, g=1, b=1;

      if (inBarrier) {
        // Tunneling Decay (Red)
        intensity = pulseIn * Math.exp(-(z - BARRIER_Z) * (5.0 - alpha * 4.0));
        r=1.0; g=0.1; b=0.1;
      } else if (pastBarrier) {
        // Emerged Wave (Cyan)
        intensity = pulseIn * (0.05 + alpha * 0.6);
        r=0.2; g=0.8; b=1.0;
      } else {
        // Interference Zone: Interaction between Incoming and Reflected
        // Before the barrier, we see both
        intensity = pulseIn + (pulseRefl * 0.6);
        
        // Color mix based on which pulse is dominant
        if (pulseRefl > pulseIn * 0.8) {
          r=0.6; g=0.2; b=1.0; // Deep Purple for Reflection
        } else {
          r=1.0; g=0.9; b=0.4; // Gold for Incident
        }
      }

      // Sine-Wave modulation for the "Absolute Truth" visual
      const wave = Math.sin(z * 3.0 - t * 15.0) * intensity * 0.6;
      posAttr[i * 3 + 0] = x + wave;
      posAttr[i * 3 + 1] = y + Math.cos(z * 3.0 - t * 15.0) * intensity * 0.6;

      colAttr[i * 3 + 0] = r;
      colAttr[i * 3 + 1] = g;
      colAttr[i * 3 + 2] = b;
    }
    meshRef.current.geometry.attributes.position.needsUpdate = true;
    meshRef.current.geometry.attributes.color.needsUpdate = true;
  });

  return (
    <group>
      <points ref={meshRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" count={points.length/3} array={points} itemSize={3} />
          <bufferAttribute attach="attributes-color" count={colors.length/3} array={colors} itemSize={3} />
        </bufferGeometry>
        <pointsMaterial size={0.07} vertexColors transparent opacity={0.75} blending={THREE.AdditiveBlending} />
      </points>

      {/* The Causal Barrier */}
      <mesh position={[0, 0, BARRIER_Z + BARRIER_WIDTH / 2]}>
        <boxGeometry args={[6, 6, BARRIER_WIDTH]} />
        <meshBasicMaterial color="#334155" transparent opacity={0.2} wireframe />
      </mesh>
    </group>
  );
}