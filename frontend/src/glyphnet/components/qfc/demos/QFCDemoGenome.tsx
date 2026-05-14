"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Float, Text } from "@react-three/drei";
import * as THREE from "three";

type QFCTopologyLike = {
  epoch: number;
  nodes: Array<{ id: string; w?: number }>;
  edges: Array<{ a: string; b: string; w?: number }>;
  gate?: number;
};

type QFCFrameLike = {
  // canonical HUD fields (preferred)
  kappa?: number; // 0..1 coherence/stability
  alpha?: number; // 0..1 optional driver

  // optional P-series fields (fallback)
  r_tail_mean?: number; // coherence-like
  f_peak?: number; // Hz

  // Stage C / topology
  topology?: QFCTopologyLike;
  topo_gate01?: number; // plumbed from HUD viewportFrame (preferred)
};

const n = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
const fract = (v: number) => v - Math.floor(v);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

const HUD_POS: [number, number, number] = [4.5, 0, 0];
const ROOT_ROT: [number, number, number] = [Math.PI / 6, 0, Math.PI / 12];
const RUNG_ROT: [number, number, number] = [Math.PI / 4, 0, Math.PI / 4];

// Workaround: some Drei/R3F type combos mis-type <Text> props in TS.
// This keeps runtime identical but unblocks builds.
const DreiText: any = Text;

function parseNodeIndex(id: string, fallback: number) {
  const m = /^n(\d+)$/.exec(String(id || ""));
  if (m) {
    const k = parseInt(m[1], 10);
    if (Number.isFinite(k)) return k;
  }
  return fallback;
}

/**
 * Genome demo (Stage C-updated):
 * - Reads topology gate (topo_gate01 preferred) and makes Genome behavior respond to it.
 * - Adds a lightweight Genome+Topology overlay (edges + nodes) driven by frame.topology.
 * - Keeps existing “active locus / nucleus” logic and palette.
 *
 * ✅ Update: dt clamp + stable time accumulator (FPS-drop stable)
 */
export default function QFCDemoGenome({ frame }: { frame: QFCFrameLike | null }) {
  const group = useRef<THREE.Group>(null);
  const coreRef = useRef<THREE.Mesh>(null);

  // ✅ dt clamp + stable time accumulator
  const tRef = useRef(0);

  // ─────────────────────────────────────────────────────────────
  // 1) Data mapping (canonical-first; clamped)
  // ─────────────────────────────────────────────────────────────
  const kappa = clamp01(n(frame?.kappa, n(frame?.r_tail_mean, 0.9989)));

  // Source frequency (Hz):
  // - Prefer real Hz (f_peak) if present.
  // - Else map alpha 0..1 → 0.20..0.70 Hz (then clamp).
  const sourceHz = (() => {
    const fp = n(frame?.f_peak, NaN);
    if (Number.isFinite(fp) && fp > 0) return clamp(fp, 0.05, 1.2);
    const a01 = clamp01(n(frame?.alpha, 0.5));
    return 0.2 + a01 * 0.5;
  })();

  // Visual breathing: sub-harmonic to keep it cinematic
  const breathHz = clamp(sourceHz * 0.22, 0.03, 0.25);

  // Stage C gate (0..1) — prefer plumbed value, fallback to topology.gate
  const topoGate01 = clamp01(n(frame?.topo_gate01, n(frame?.topology?.gate, 1)));

  // ─────────────────────────────────────────────────────────────
  // Styling constants (same vibe, darker palette)
  // ─────────────────────────────────────────────────────────────
  const HELIX_PURPLE = "#3b168a"; // darker violet
  const HELIX_GREEN = "#064e3b"; // darker emerald
  const TOPO_CYAN = "#38bdf8"; // topology overlay tint (readable)

  const radiusBase = 2.2;
  const height = 12;
  const turns = 3;

  // Topology gate drives genome behavior:
  const radius = radiusBase * lerp(0.88, 1.16, topoGate01);

  // temp vectors (avoid per-frame allocations)
  const tmpA = useRef(new THREE.Vector3());
  const tmpB = useRef(new THREE.Vector3());
  const tmpMid = useRef(new THREE.Vector3());

  // ─────────────────────────────────────────────────────────────
  // 2) Geometry (recomputed only when radius/height/turns change)
  // ─────────────────────────────────────────────────────────────
  const { curveA, curveB, rungs } = useMemo(() => {
    const pointsA: THREE.Vector3[] = [];
    const pointsB: THREE.Vector3[] = [];
    const count = 60;

    const items: Array<{
      id: number;
      mid: THREE.Vector3;
      quat: THREE.Quaternion;
      len: number;
      color: string;
    }> = [];

    const up = new THREE.Vector3(0, 1, 0);

    for (let i = 0; i <= count; i++) {
      const tt = (i / count) * Math.PI * 2 * turns;
      const y = (i / count) * height - height / 2;

      const pA = new THREE.Vector3(Math.cos(tt) * radius, y, Math.sin(tt) * radius);
      const pB = new THREE.Vector3(Math.cos(tt + Math.PI) * radius, y, Math.sin(tt + Math.PI) * radius);

      pointsA.push(pA);
      pointsB.push(pB);

      // rung every ~3 segments
      if (i % 3 === 0 && i < count) {
        const mid = new THREE.Vector3().addVectors(pA, pB).multiplyScalar(0.5);
        const dir = new THREE.Vector3().subVectors(pB, pA);
        const len = dir.length();

        dir.normalize();
        const quat = new THREE.Quaternion().setFromUnitVectors(up, dir);

        const color = items.length % 2 === 0 ? HELIX_PURPLE : HELIX_GREEN;
        items.push({ id: i, mid, quat, len, color });
      }
    }

    return {
      curveA: new THREE.CatmullRomCurve3(pointsA),
      curveB: new THREE.CatmullRomCurve3(pointsB),
      rungs: items,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [radius, height, turns]);

  // Helper: midpoint between strands at parameter u (0..1)
  const getMidpointAt = (u: number, out: THREE.Vector3) => {
    curveA.getPointAt(u, tmpA.current);
    curveB.getPointAt(u, tmpB.current);
    out.copy(tmpA.current).add(tmpB.current).multiplyScalar(0.5);
    return out;
  };

  // ─────────────────────────────────────────────────────────────
  // 2b) Topology overlay geometry (edges + nodes)
  // ─────────────────────────────────────────────────────────────
  const topology = frame?.topology ?? null;

  const topoKey = useMemo(() => {
    const epoch = topology?.epoch ?? 0;
    const nn = topology?.nodes?.length ?? 0;
    const ee = topology?.edges?.length ?? 0;
    const gate = n(topology?.gate, topoGate01).toFixed(3);
    return `${epoch}:${nn}:${ee}:${gate}`;
  }, [topology?.epoch, topology?.nodes?.length, topology?.edges?.length, topology?.gate, topoGate01]);

  const topoOverlay = useMemo(() => {
    if (!topology || !Array.isArray(topology.nodes) || !Array.isArray(topology.edges)) {
      return {
        nodePositions: [] as THREE.Vector3[],
        edgePositions: new Float32Array(0),
        has: false,
        epoch: 0,
      };
    }

    const nodes = topology.nodes;
    const edges = topology.edges;

    const N = Math.max(1, nodes.length);
    const epoch = Number(topology.epoch ?? 0);

    // Small, stable epoch offset so successive epochs “shift” attachment points
    const epochOffset = ((epoch % N) / N) * 0.35;

    const nodePos: THREE.Vector3[] = new Array(N);
    const idToPos = new Map<string, THREE.Vector3>();

    for (let i = 0; i < N; i++) {
      const node = nodes[i];
      const idx = parseNodeIndex(node?.id ?? `n${i}`, i);
      const u = fract(idx / N + epochOffset);

      const p = new THREE.Vector3();
      getMidpointAt(u, p);

      // Slight radial lift so edges hover above the helix core
      const radial = new THREE.Vector3(p.x, 0, p.z);
      if (radial.lengthSq() > 1e-6) radial.normalize().multiplyScalar(0.35);
      p.add(radial);

      nodePos[i] = p;
      idToPos.set(String(node?.id ?? `n${i}`), p);
    }

    const buf = new Float32Array(edges.length * 2 * 3);
    let w = 0;

    for (let i = 0; i < edges.length; i++) {
      const e = edges[i];
      const a = idToPos.get(String(e?.a ?? "")) ?? nodePos[parseNodeIndex(String(e?.a ?? ""), 0) % N];
      const b = idToPos.get(String(e?.b ?? "")) ?? nodePos[parseNodeIndex(String(e?.b ?? ""), 1) % N];

      buf[w++] = a.x;
      buf[w++] = a.y;
      buf[w++] = a.z;

      buf[w++] = b.x;
      buf[w++] = b.y;
      buf[w++] = b.z;
    }

    return {
      nodePositions: nodePos,
      edgePositions: buf,
      has: true,
      epoch,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topoKey, curveA, curveB]);

  // ─────────────────────────────────────────────────────────────
  // 3) Animation (dtc + stable time)
  // ─────────────────────────────────────────────────────────────
  useFrame((_state, dtRaw) => {
    if (!group.current) return;

    // ✅ dt clamp
    const dtc = Math.min(dtRaw, 1 / 30);

    // ✅ stable time accumulator
    tRef.current += dtc;
    const t = tRef.current;

    // Gate makes rotation “more alive” as it opens
    const rotRate = 0.10 + kappa * 0.10 + topoGate01 * 0.20;
    group.current.rotation.y += dtc * rotRate;
    group.current.rotation.z = Math.sin(t * 0.18) * lerp(0.06, 0.12, topoGate01);

    // Gate increases breathing amplitude slightly
    const amp = 0.010 * (0.7 + 0.3 * kappa) * lerp(0.85, 1.35, topoGate01);
    const pulse = 1 + Math.sin(t * breathHz * Math.PI * 2) * amp;
    group.current.scale.setScalar(pulse);

    // ACTIVE LOCUS / nucleus position
    if (coreRef.current) {
      const travelRate =
        0.022 + (1 - kappa) * 0.028 + clamp(sourceHz, 0.05, 1.2) * 0.008 + topoGate01 * 0.020;

      const u = fract(t * travelRate + 0.15 * Math.sin(t * 0.07));
      getMidpointAt(u, tmpMid.current);

      tmpMid.current.y += Math.sin(t * 0.35) * 0.05 * (0.6 + 0.4 * kappa);
      tmpMid.current.y += lerp(0.0, 0.18, topoGate01);

      coreRef.current.position.copy(tmpMid.current);
    }
  });

  // Gate-driven emissive intensity scaling
  const strandEmissiveA = 1.15 * lerp(0.85, 1.55, topoGate01);
  const strandEmissiveB = 1.05 * lerp(0.85, 1.45, topoGate01);
  const rungOpacity = lerp(0.18, 0.52, topoGate01);
  const nodeOpacity = lerp(0.1, 0.65, topoGate01);
  const edgeOpacity = lerp(0.06, 0.42, topoGate01);

  // Status text extras
  const epochText = topology?.epoch != null ? String(topology.epoch) : "—";
  const topoNodes = topology?.nodes?.length ?? 0;
  const topoEdges = topology?.edges?.length ?? 0;

  return (
    <group ref={group} rotation={ROOT_ROT}>
      {/* Strand A (purple) */}
      <mesh>
        <tubeGeometry args={[curveA, 64, 0.06, 8, false]} />
        <meshStandardMaterial color={HELIX_PURPLE} emissive={HELIX_PURPLE} emissiveIntensity={strandEmissiveA} />
      </mesh>

      {/* Strand B (green) */}
      <mesh>
        <tubeGeometry args={[curveB, 64, 0.06, 8, false]} />
        <meshStandardMaterial color={HELIX_GREEN} emissive={HELIX_GREEN} emissiveIntensity={strandEmissiveB} />
      </mesh>

      {/* Rungs */}
      {rungs.map((seg) => (
        <group key={seg.id}>
          <mesh position={seg.mid} quaternion={seg.quat}>
            <cylinderGeometry args={[0.02, 0.02, seg.len, 8]} />
            <meshBasicMaterial color={seg.color} transparent opacity={rungOpacity} />
          </mesh>

          <mesh position={seg.mid} rotation={RUNG_ROT}>
            <octahedronGeometry args={[0.17]} />
            <meshStandardMaterial
              color={seg.color}
              emissive={seg.color}
              emissiveIntensity={4.2 * (0.7 + 0.3 * kappa) * lerp(0.9, 1.25, topoGate01)}
            />
          </mesh>
        </group>
      ))}

      {/* Topology overlay */}
      {topoOverlay.has ? (
        <group>
          <lineSegments>
            <bufferGeometry>
              <bufferAttribute
                attach="attributes-position"
                array={topoOverlay.edgePositions}
                count={topoOverlay.edgePositions.length / 3}
                itemSize={3}
              />
            </bufferGeometry>
            <lineBasicMaterial color={TOPO_CYAN} transparent opacity={edgeOpacity} />
          </lineSegments>

          {topoOverlay.nodePositions.map((p, i) => (
            <mesh key={`tn:${i}`} position={p}>
              <sphereGeometry args={[0.1, 14, 14]} />
              <meshStandardMaterial
                color={TOPO_CYAN}
                emissive={TOPO_CYAN}
                emissiveIntensity={lerp(0.8, 3.0, topoGate01)}
                transparent
                opacity={nodeOpacity}
              />
            </mesh>
          ))}
        </group>
      ) : null}

      {/* ACTIVE LOCUS / NUCLEUS */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[0.55, 48, 48]} />
        <meshPhysicalMaterial
          transparent
          transmission={1}
          thickness={0.9}
          roughness={0.18}
          ior={1.35}
          color="#1b0b3a"
          attenuationColor="#14072a"
          attenuationDistance={0.7}
          clearcoat={0.7}
          clearcoatRoughness={0.22}
          envMapIntensity={1.05}
        />
      </mesh>

      <Clouds count={400} opacity={lerp(0.22, 0.4, topoGate01)} />

      <Float speed={2} rotationIntensity={0.2} floatIntensity={0.5}>
        <DreiText position={HUD_POS} fontSize={0.22} color={HELIX_GREEN} font="/fonts/SpaceMono-Regular.ttf" maxWidth={3}>
          {`GENOME_ACTIVE_LOCUS
COHERENCE: ${kappa.toFixed(5)}
GATE: ${topoGate01.toFixed(3)} | EPOCH: ${epochText}
TOPO: nodes=${topoNodes} edges=${topoEdges}
SRC_HZ: ${sourceHz.toFixed(3)} | BREATH_HZ: ${breathHz.toFixed(3)}
STATUS: PASS_CERTIFIED`}
        </DreiText>
      </Float>
    </group>
  );
}

function Clouds({ count, opacity = 0.35 }: { count: number; opacity?: number }) {
  const points = useMemo(() => {
    const p = new Float32Array(count * 3);
    for (let i = 0; i < p.length; i++) p[i] = (Math.random() - 0.5) * 25;
    return p;
  }, [count]);

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={count} array={points} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.04} color="#ffffff" transparent opacity={opacity} sizeAttenuation />
    </points>
  );
}