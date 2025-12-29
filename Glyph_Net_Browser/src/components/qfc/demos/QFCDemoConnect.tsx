"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

export default function QFCDemoConnect({ frame }: { frame: any }) {
  const nodesRef = useRef<THREE.Group>(null);
  const lineMaterialRef = useRef<THREE.ShaderMaterial>(null);

  // Initialize nodes as "Information Hubs"
  const nodes = useMemo(() => {
    return Array.from({ length: 12 }).map((_, i) => ({
      id: i,
      phaseOffset: Math.random() * Math.PI * 2,
      basePos: new THREE.Vector3(
        (Math.random() - 0.5) * 12,
        (Math.random() - 0.5) * 6 + 1,
        (Math.random() - 0.5) * 12
      ),
    }));
  }, []);

  // Custom Shader for "Entanglement Threads"
  const lineShader = useMemo(() => ({
    uniforms: {
      uTime: { value: 0 },
      uCoupling: { value: 0.5 },
      uAlpha: { value: 0.2 },
    },
    vertexShader: `
      varying float vProgress;
      uniform float uTime;
      uniform float uCoupling;
      void main() {
        vProgress = uv.x;
        vec3 pos = position;
        // Subtle vibration of the thread based on coupling resonance
        pos.y += sin(pos.x * 2.0 + uTime * 3.0) * 0.05 * uCoupling;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
      }
    `,
    fragmentShader: `
      varying float vProgress;
      uniform float uTime;
      uniform float uCoupling;
      uniform float uAlpha;
      void main() {
        // Soliton "Packet" moving along the line
        float packet = smoothstep(0.45, 0.5, 1.0 - fract(vProgress - uTime * (0.5 + uCoupling)));
        vec3 color = mix(vec3(0.0, 0.4, 0.6), vec3(0.2, 0.9, 1.0), packet);
        float alpha = (0.1 + packet * 0.8) * uAlpha * (0.3 + uCoupling * 0.7);
        gl_FragColor = vec4(color, alpha);
      }
    `
  }), []);

  const lineGeom = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    const indices = [];
    const vertices = [];
    const uvs = [];
    
    // Connect each node to 2 neighbors to create a "Causal Loop"
    let vIdx = 0;
    for (let i = 0; i < nodes.length; i++) {
      for (let j = 1; j <= 2; j++) {
        const next = (i + j) % nodes.length;
        vertices.push(0, 0, 0, 0, 0, 0); // Placeholder
        uvs.push(0, 0, 1, 0); // 0 at start, 1 at end for the shader packet
        indices.push(vIdx++, vIdx++);
      }
    }
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
    geometry.setIndex(indices);
    return geometry;
  }, [nodes]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const coupling = frame?.coupling_score ?? 0.5;
    const alpha = frame?.alpha ?? 0.3;

    if (lineMaterialRef.current) {
      lineMaterialRef.current.uniforms.uTime.value = t;
      lineMaterialRef.current.uniforms.uCoupling.value = coupling;
      lineMaterialRef.current.uniforms.uAlpha.value = alpha;
    }

    const currentPositions: THREE.Vector3[] = nodes.map(n => {
      const p = n.basePos.clone();
      // Orbiting motion influenced by coupling
      const radius = 1.5 * (1.0 - coupling * 0.5);
      p.x += Math.cos(t * 0.5 + n.phaseOffset) * radius;
      p.z += Math.sin(t * 0.5 + n.phaseOffset) * radius;
      p.y += Math.sin(t * 0.8 + n.phaseOffset) * 0.5;
      return p;
    });

    // Update Lines
    const posAttr = lineGeom.getAttribute("position");
    let lIdx = 0;
    for (let i = 0; i < nodes.length; i++) {
      for (let j = 1; j <= 2; j++) {
        const next = (i + j) % nodes.length;
        const start = currentPositions[i];
        const end = currentPositions[next];
        posAttr.setXYZ(lIdx++, start.x, start.y, start.z);
        posAttr.setXYZ(lIdx++, end.x, end.y, end.z);
      }
    }
    posAttr.needsUpdate = true;

    // Update Node Meshes
    if (nodesRef.current) {
      nodesRef.current.children.forEach((child, i) => {
        child.position.copy(currentPositions[i]);
        const scale = 0.2 + coupling * 0.4;
        child.scale.setScalar(scale);
      });
    }
  });

  return (
    <group>
      <lineSegments geometry={lineGeom}>
        <shaderMaterial 
          ref={lineMaterialRef}
          {...lineShader}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </lineSegments>

      <group ref={nodesRef}>
        {nodes.map((n) => (
          <mesh key={n.id}>
            <sphereGeometry args={[0.3, 16, 16]} />
            <meshBasicMaterial color="#22d3ee" transparent opacity={0.8} />
            {/* Inner "Nucleus" */}
            <mesh scale={0.5}>
              <sphereGeometry args={[0.3, 8, 8]} />
              <meshBasicMaterial color="#ffffff" />
            </mesh>
          </mesh>
        ))}
      </group>
    </group>
  );
}