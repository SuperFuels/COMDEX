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
  const half = (n - 1) / 2;
  const X = x - half;
  const Z = y - half;
  return new THREE.Vector3(X, 0, Z);
}

// ---------- Dot-man geometry helpers ----------
function randOnSphere(r: number) {
  const u = Math.random();
  const v = Math.random();
  const theta = 2 * Math.PI * u;
  const phi = Math.acos(2 * v - 1);
  const x = r * Math.sin(phi) * Math.cos(theta);
  const y = r * Math.sin(phi) * Math.sin(theta);
  const z = r * Math.cos(phi);
  return [x, y, z] as const;
}

function pushSphere(points: number[], cx: number, cy: number, cz: number, r: number, count: number) {
  for (let i = 0; i < count; i++) {
    const [x, y, z] = randOnSphere(r);
    points.push(cx + x, cy + y, cz + z);
  }
}

function pushCylinder(points: number[], cx: number, cy0: number, cy1: number, cz: number, r: number, count: number) {
  for (let i = 0; i < count; i++) {
    const t = Math.random();
    const y = cy0 + (cy1 - cy0) * t;
    const a = Math.random() * Math.PI * 2;
    const x = Math.cos(a) * r;
    const z = Math.sin(a) * r;
    points.push(cx + x, y, cz + z);
  }
}

function buildDotManGeometry() {
  const pts: number[] = [];
  pushSphere(pts, 0, 0.55, 0, 0.22, 180);
  pushCylinder(pts, 0, 0.10, 0.48, 0, 0.18, 220);
  pushCylinder(pts, -0.22, 0.22, 0.42, 0, 0.07, 90);
  pushCylinder(pts, +0.22, 0.22, 0.42, 0, 0.07, 90);
  pushCylinder(pts, -0.10, -0.22, 0.12, 0, 0.08, 120);
  pushCylinder(pts, +0.10, -0.22, 0.12, 0, 0.08, 120);

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
  geo.computeBoundingSphere();
  return geo;
}

export default function QFCDemoReflexGrid(props: { frame: any }) {
  // ✅ PRIMARY: take reflex state from the injected frame (no polling needed when wired)
  const stFromFrame: ReflexState | null =
    (props?.frame?.reflex as ReflexState) ??
    (props?.frame?.reflex?.state as ReflexState) ??
    null;

  // ✅ fallback (only used if frame is missing)
  const [stFallback, setStFallback] = useState<ReflexState | null>(null);

  const API_BASE =
    (typeof window !== "undefined" && (window as any).__API_BASE__) ||
    ""; // same-origin

  // ✅ start the bounded backend runner once per open window
  const startedRef = useRef(false);
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    fetch(`${API_BASE}/api/demo/reflex/run`, { method: "POST" }).catch(() => {});
  }, [API_BASE]);

  // ✅ fallback poll (ONLY when frame isn't feeding state)
  useEffect(() => {
    if (stFromFrame) return;

    let alive = true;

    const tick = async () => {
      try {
        // ✅ FIX: do NOT hardcode /aion-demo here; your FE expects /api/*
        const r = await fetch(`${API_BASE}/api/reflex`, { cache: "no-store" });
        const j: Envelope = await r.json();
        if (!alive) return;
        setStFallback(j?.state ?? null);
      } catch {
        if (!alive) return;
        setStFallback(null);
      }
    };

    tick();
    const iv = setInterval(tick, 250);
    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, [API_BASE, stFromFrame]);

  const st = stFromFrame ?? stFallback;

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

  // dot-man rig
  const rigRef = useRef<THREE.Group>(null);
  const matRef = useRef<THREE.PointsMaterial>(null);
  const target = useMemo(() => new THREE.Vector3(), []);
  const dotManGeo = useMemo(() => buildDotManGeometry(), []);

  useFrame((state, dtRaw) => {
    const dt = Math.min(dtRaw, 1 / 30);

    if (rigRef.current) {
      target.copy(gridToWorld(pos.x, pos.y, n));
      target.y = -1.55;
      rigRef.current.position.lerp(target, 1 - Math.pow(0.001, dt));

      const t = state.clock.getElapsedTime();
      rigRef.current.position.y = target.y + 0.05 * Math.sin(t * 7.0);
      rigRef.current.rotation.y = 0.25 * Math.sin(t * 3.0);
    }

    if (matRef.current) {
      const t = state.clock.getElapsedTime();
      matRef.current.size = 0.06 + 0.015 * Math.sin(t * 6.0);
      matRef.current.needsUpdate = true;
    }
  });

  return (
    <group>
      {/* Base grid plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.95, 0]}>
        <planeGeometry args={[n, n]} />
        <meshStandardMaterial color={danger ? "#12060a" : "#050a14"} />
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

      {/* Dot-man avatar */}
      <group ref={rigRef}>
        <points geometry={dotManGeo}>
          <pointsMaterial
            ref={matRef}
            size={0.06}
            sizeAttenuation
            transparent
            opacity={0.95}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
            color={danger ? "#ff4d6d" : "#7dd3fc"}
          />
        </points>

        {/* tiny “core” glow */}
        <mesh position={[0, 0.28, 0]}>
          <sphereGeometry args={[0.10, 16, 16]} />
          <meshStandardMaterial
            color={"#e2e8f0"}
            emissive={danger ? "#ff4d6d" : "#7dd3fc"}
            emissiveIntensity={1.25}
            transparent
            opacity={0.7}
          />
        </mesh>
      </group>
    </group>
  );
}