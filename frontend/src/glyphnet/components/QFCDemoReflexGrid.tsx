"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

type ReflexState = {
  grid_size?: number;
  position?: { x: number; y: number };
  world?: Record<string, string>;
  last_event_type?: string;
  stability_breached?: boolean;
};

type Envelope = { state?: ReflexState | null };

function parseKey(k: string): [number, number] | null {
  const parts = String(k).split(",");
  if (parts.length !== 2) return null;
  const x = Number(parts[0]);
  const y = Number(parts[1]);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  return [x, y];
}

function gridToWorld(x: number, y: number, n: number) {
  // center the grid at origin; map (x,y) -> (X,Z)
  const half = (n - 1) / 2;
  const X = x - half;
  const Z = y - half;
  return new THREE.Vector3(X, 0, Z);
}

export default function QFCDemoReflexGrid(_: { frame: any }) {
  const [st, setSt] = useState<ReflexState | null>(null);

  // ✅ point this at whatever your browser app uses as API base
  // If you already have a central helper, swap this to use it.
  const API_BASE =
    (typeof window !== "undefined" && (window as any).__API_BASE__) ||
    ""; // "" -> same-origin

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const r = await fetch(`${API_BASE}/api/reflex`, { cache: "no-store" });
        const j: Envelope = await r.json();
        if (!alive) return;
        setSt(j?.state ?? null);
      } catch {
        if (!alive) return;
        setSt(null);
      }
    };

    tick();
    const iv = setInterval(tick, 200);
    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, [API_BASE]);

  const n = st?.grid_size ?? 10;
  const pos = st?.position ?? { x: 0, y: 0 };
  const danger = st?.last_event_type === "danger" || !!st?.stability_breached;

  const markers = useMemo(() => {
    const world = st?.world ?? {};
    const out: Array<{ x: number; y: number; token: string }> = [];
    for (const [k, token] of Object.entries(world)) {
      const xy = parseKey(k);
      if (!xy) continue;
      out.push({ x: xy[0], y: xy[1], token });
    }
    return out;
  }, [st]);

  // agent mesh
  const agentRef = useRef<THREE.Mesh>(null);
  const target = useMemo(() => new THREE.Vector3(), []);
  useFrame(() => {
    if (!agentRef.current) return;
    target.copy(gridToWorld(pos.x, pos.y, n));
    target.y = 0.45;
    agentRef.current.position.lerp(target, 0.22);
  });

  return (
    <group>
      {/* Base grid plane (slightly above the QFC ground) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.95, 0]}>
        <planeGeometry args={[n, n]} />
        <meshStandardMaterial color={danger ? "#1a0b0b" : "#050a14"} />
      </mesh>

      {/* World markers */}
      {markers.map((m, i) => {
        const p = gridToWorld(m.x, m.y, n);
        p.y = -1.60;

        const isDanger = m.token === "pit" || m.token === "spike";
        const isObj = ["bed", "desk", "coffee", "window"].includes(m.token);
        const isSym = !isDanger && !isObj && m.token.length === 1;

        const h = isDanger ? 1.1 : isObj ? 0.8 : isSym ? 0.6 : 0.5;

        return (
          <mesh key={`${m.token}:${i}`} position={[p.x, p.y + h / 2, p.z]}>
            <boxGeometry args={[0.72, h, 0.72]} />
            <meshStandardMaterial
              color={isDanger ? "#7f1d1d" : isObj ? "#0b1220" : "#111827"}
              emissive={isDanger ? "#ff3b3b" : isSym ? "#38bdf8" : "#000000"}
              emissiveIntensity={isDanger ? 0.9 : isSym ? 0.65 : 0.0}
            />
          </mesh>
        );
      })}

      {/* Agent avatar */}
      <mesh ref={agentRef}>
        <sphereGeometry args={[0.38, 28, 28]} />
        <meshStandardMaterial
          color={"#e2e8f0"}
          emissive={danger ? "#fb7185" : "#7dd3fc"}
          emissiveIntensity={0.95}
        />
      </mesh>
    </group>
  );
}