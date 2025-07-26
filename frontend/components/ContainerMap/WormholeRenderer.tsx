import React, { useRef, useMemo, useState, useEffect } from 'react';
import * as THREE from 'three';
import { useFrame, extend, ReactThreeFiber } from '@react-three/fiber';
import { TextGeometry } from 'three/examples/jsm/geometries/TextGeometry';
import { FontLoader, Font } from 'three/examples/jsm/loaders/FontLoader';
import helvetiker from 'three/examples/fonts/helvetiker_regular.typeface.json';

extend({ TextGeometry });

interface WormholeRendererProps {
  from: [number, number, number];
  to: [number, number, number];
  color?: string;
  thickness?: number;
  glyph?: string;
  mode?: 'solid' | 'dashed' | 'glow';
  pulse?: boolean;
  pulseFlow?: boolean;
}

declare global {
  namespace JSX {
    interface IntrinsicElements {
      textGeometry: ReactThreeFiber.Object3DNode<TextGeometry, typeof TextGeometry>;
    }
  }
}

export default function WormholeRenderer({
  from,
  to,
  color = '#ff00ff',
  thickness = 0.02,
  glyph,
  mode = 'glow',
  pulse = false,
  pulseFlow = false,
}: WormholeRendererProps) {
  const lineRef = useRef<THREE.Line>(null);
  const textRef = useRef<THREE.Mesh>(null);

  const points = useMemo(() => {
    return [new THREE.Vector3(...from), new THREE.Vector3(...to)];
  }, [from, to]);

  const geometry = useMemo(() => {
    return new THREE.BufferGeometry().setFromPoints(points);
  }, [points]);

  const material = useMemo(() => {
    const mat = new THREE.LineBasicMaterial({
      color,
      linewidth: thickness,
      transparent: true,
      opacity: mode === 'glow' ? 0.7 : 1,
    });

    if (mode === 'glow') {
      mat.depthWrite = false;
      mat.blending = THREE.AdditiveBlending;
    }

    return mat;
  }, [color, thickness, mode]);

  const font = useMemo(() => {
    const loader = new FontLoader();
    return loader.parse(helvetiker as any) as Font;
  }, []);

  useFrame(({ clock }) => {
    if (pulse && lineRef.current?.material instanceof THREE.Material) {
      const intensity = 0.5 + 0.5 * Math.sin(clock.elapsedTime * 4);
      lineRef.current.material.opacity = intensity;
      lineRef.current.material.needsUpdate = true;
    }
  });

  return (
    <>
      <primitive object={new THREE.Line(geometry, material)} ref={lineRef} />
      {glyph && font && (
        <mesh
          ref={textRef}
          position={new THREE.Vector3().addVectors(points[0], points[1]).multiplyScalar(0.5)}
        >
          <textGeometry args={[glyph, { font, size: 0.3, depth: 0.05 }]} attach="geometry" />
          <meshStandardMaterial
            attach="material"
            color={color}
            emissive={color}
            emissiveIntensity={1.5}
          />
        </mesh>
      )}
    </>
  );
}