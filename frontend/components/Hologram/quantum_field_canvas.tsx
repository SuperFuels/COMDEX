// File: frontend/components/Hologram/quantum_field_canvas.tsx

import React, { useRef, useEffect, useState, useMemo, useCallback } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useSharedField } from "../../../collab/useSharedField";
import { PresenceLayer } from "../../../collab/PresenceLayer";
// Keep your existing feature imports
import { QWaveBeam, BeamProps } from "@/components/QuantumField/beam_renderer";
import TraceCollapseRenderer from "@/components/QuantumField/Replay/trace_collapse_renderer";
import { snapToEntangledMemoryLayout } from "@/lib/layout";
import { useQfcSocket } from "@/hooks/useQfcSocket";
import HoverAgentLogicView from "@/components/QuantumField/Memory/hover_agent_logic_view";
import { QWavePreviewPanel } from "@/components/QuantumField/QWavePreviewPanel";

// 🔧 Import shape fixes from your earlier errors
import EntropyNode from "@/components/QuantumField/styling/EntropyNode"; // default
import { HighlightedOperator } from "@/components/QuantumField/highlighted_symbolic_operators"; // named

import PredictedLayerRenderer from "@/components/QuantumField/PredictedLayerRenderer";
import ClusterZoomRenderer from "@/components/QuantumField/cluster_zoom_renderer";
import EmotionOverlay from "@/components/QuantumField/EmotionOverlay";
import ScrollReplayOverlay from "@/components/QuantumField/ScrollReplayOverlay";
import StrategyOverlay from "@/components/QuantumField/StrategyOverlay";
import ObserverViewport from "@/components/QuantumField/ObserverViewport";
import MemoryScroller from "@/components/QuantumField/MemoryScroller";
import HoverMutationTrace from "@/components/QuantumField/HoverMutationTrace";
import MultiNodeCollapseTrail from "@/components/QuantumField/MultiNodeCollapseTrail";
import BreakthroughDeadendTrail from "@/components/QuantumField/BreakthroughDeadendTrail";
import BeamLogicOverlay from "@/components/QuantumField/BeamLogicOverlay";
import { rerouteBeam } from "@/components/QuantumField/beam_rerouter";
import { useQFCFocus } from "@/hooks/useQFCFocus";
import { GlyphNode } from "@/types/qfc";
import {
  HtmlEmotionPulse,
  MeshEmotionPulse,
} from "@/components/QuantumField/EmotionPulseOverlay";
import HolographicCausalityTrails, {
  CausalityTrailSegment,
} from "@/components/QuantumField/Replay/holographic_causality_trails";
import HoverMemorySummary from "@/components/Hologram/HoverMemorySummary";
import * as TWEEN from "@tweenjs/tween.js";

// ------------------ Types ------------------

interface Link {
  source: string;
  target: string;
  type?: "entangled" | "teleport" | "logic";
  tick?: number;
}

// Extend base GlyphNode with UI-only flags used in this canvas.
type ExtendedGlyphNode = GlyphNode & {
  id?: string | number;
  position: [number, number, number];
  containerId?: string;
  predicted?: boolean;
  locked?: boolean;
  color?: string;
  label?: string;
  emotion?: { type?: string; intensity?: number } | boolean;
};

interface QuantumFieldCanvasProps {
  /** Base graph data (local or preloaded) */
  nodes: ExtendedGlyphNode[];
  links: Link[];

  /** Optional: beams used as a local/fallback source when collaboration is empty */
  beams?: any[];

  /** UI options */
  tickFilter?: number;
  showCollapsed?: boolean;
  onTeleport?: (targetContainerId: string) => void;

  /** Collaborative room id (optional). If omitted, use "default" inside the component */
  containerId?: string;

  /** Optional overlay props */
  predictedMode?: boolean;
  predictedOverlay?: {
    nodes: ExtendedGlyphNode[];
    links: Link[];
  };
}

// ------------------ Small helpers ------------------

// Local shim to mirror backend "broadcast_qfc_update" semantics.
// Safe in browser; no-op during SSR.
function broadcast_qfc_update(payload: any) {
  try {
    window.dispatchEvent(new CustomEvent("qfc_update", { detail: payload }));
  } catch {
    /* no-op */
  }
}

// 🎨 Get link color by type
const getLinkColor = (type?: string): string => {
  switch (type) {
    case "entangled":
      return "#ff66ff";
    case "teleport":
      return "#00ffff";
    case "logic":
      return "#66ff66";
    default:
      return "#8888ff";
  }
};

// ─────────────────────────────────────────────────────────────
// Keep these TWO helpers exported at TOP LEVEL (outside component)
// ─────────────────────────────────────────────────────────────

/** Move camera/controls to a node (by id). Tween when possible; snap otherwise. */
export function setOrbitTargetToGlyphFactory(opts: {
  nodes: Array<{ id: string | number; position: [number, number, number] }>;
  cameraRef: React.RefObject<THREE.PerspectiveCamera>;
  controlsRef: React.RefObject<any>; // OrbitControls
}) {
  const { nodes, cameraRef, controlsRef } = opts;

  return (glyphId: string | number) => {
    const n = nodes.find((x: any) => String(x?.id) === String(glyphId));
    if (!n || !controlsRef.current) return;

    const target = new THREE.Vector3(n.position[0], n.position[1], n.position[2]);

    // Try tween.js if present; otherwise snap.
    const maybeTween = (globalThis as any).TWEEN;
    if (maybeTween && cameraRef.current) {
      const TWEEN = maybeTween;

      new TWEEN.Tween(controlsRef.current.target)
        .to({ x: target.x, y: target.y, z: target.z }, 900)
        .easing(TWEEN.Easing.Quadratic.Out)
        .onUpdate(() => controlsRef.current.update?.())
        .start();

      const camPos = cameraRef.current.position.clone();
      new TWEEN.Tween(camPos)
        .to({ x: target.x + 5, y: target.y + 5, z: target.z + 5 }, 900)
        .easing(TWEEN.Easing.Quadratic.Out)
        .onUpdate(() => {
          if (!cameraRef.current) return;
          cameraRef.current.position.set(camPos.x, camPos.y, camPos.z);
          controlsRef.current.update?.();
        })
        .start();
    } else {
      try {
        controlsRef.current.target.copy(target);
        controlsRef.current.update?.();
      } catch {
        /* no-op */
      }
    }
  };
}

/** Center by glyph id/label using merged nodes (de-duped & safe) */
export function centerToGlyphFactory(opts: {
  mergedNodes: Array<{ id?: string | number; glyph?: string | number; position: [number, number, number] }>;
  setObserverPosition: React.Dispatch<React.SetStateAction<[number, number, number]>>;
  setOrbitTargetToGlyph: (glyphId: string | number) => void;
}) {
  const { mergedNodes, setObserverPosition, setOrbitTargetToGlyph } = opts;

  return (glyphOrId: string | number) => {
    const key = String(glyphOrId);
    const node = mergedNodes.find(
      (n: any) => String(n?.id ?? "") === key || String(n?.glyph ?? "") === key
    );
    if (!node) {
      console.warn("❌ Glyph not found in nodes:", glyphOrId);
      return;
    }

    setObserverPosition(node.position as [number, number, number]);
    setOrbitTargetToGlyph((node as any).id ?? glyphOrId);
  };
}

// ------------------ Main Component ------------------

export default function QuantumFieldCanvas(props: QuantumFieldCanvasProps) {
  const [showPredictedLayer, setShowPredictedLayer] = useState(false);
  const [predictedMode, setPredictedMode] = useState(!!props.predictedMode);
  const [predictedOverlay, setPredictedOverlay] = useState(!!props.predictedOverlay);
  const [splitScreen, setSplitScreen] = useState(false);

  const [selectedBeam, setSelectedBeam] = useState<any | null>(null);
  const [beams, setBeams] = useState<any[]>([]);
  const [graphAdds, setGraphAdds] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });

  // --- Camera & controls -------------------------------------------
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<any>(null); // OrbitControls

  // Some builds of useQFCFocus don't expose setFocus; guard it so TS is happy.
  const qfcFocus = (typeof useQFCFocus === "function" ? useQFCFocus() : null) as any;
  const setFocus: (id: string) => void =
    qfcFocus && typeof qfcFocus.setFocus === "function" ? qfcFocus.setFocus : () => {};

  // --- Branch / observer state -------------------------------------
  const [selectedBranch, setSelectedBranch] = useState("trail-1");
  const availableBranches = ["trail-1", "trail-2", "trail-3"];

  const [observerPosition, setObserverPosition] = useState<[number, number, number]>([0, 0, 0]);
  const observerDirection: [number, number, number] = [0, 0, -1]; // forward

  // --- Beams + replay state ----------------------------------------
  const [beamData, setBeamData] = useState<any[] | null>([]);
  const [replayFrames, setReplayFrames] = useState<any[]>([]);
  const [isReplaying, setIsReplaying] = useState(false);
  const [playbackIndex, setPlaybackIndex] = useState(0);

// 1) Load beams exactly like before (but via the hook)
useLoadQWaveBeamsLocal(setBeamData);

// 2) Trails (memoized once to avoid redeclare issues)
const { collapseTrails, breakthroughTrails, deadendTrails } = useMemo(
  getStaticTrailsLocal,
  []
);

// pull from props (containerId may be undefined)
// pull from props (containerId may be undefined)
const { tickFilter, showCollapsed = false, containerId } = props;

// pick a safe room id
const roomId = containerId ?? "default";

// connect to shared field (CRDT)
const {
  nodes: sharedNodes,
  links: sharedLinks,
  beams: sharedBeams,
  applyOp,
  others,
} = useSharedField(roomId);

/**
 * Normalize shared state to the same shape as props:
 * - ensure label is a string (fallback to id)
 * - ensure position is a Vec3
 * - coerce link endpoints to strings
 */
const normSharedNodes = useMemo<ExtendedGlyphNode[]>(
  () =>
    (sharedNodes ?? []).map((n: any) => ({
      ...n,
      id: n.id,
      position: (n.position ?? [0, 0, 0]) as [number, number, number],
      label: typeof n.label === "string" ? n.label : String(n.id ?? ""),
    })),
  [sharedNodes]
);

const normSharedLinks = useMemo<Link[]>(
  () =>
    (sharedLinks ?? []).map((l: any) => ({
      ...l,
      source: String(l.source),
      target: String(l.target),
    })),
  [sharedLinks]
);

// ✅ Prefer shared CRDT data; fall back to existing local sources (types now match)
const nodes: ExtendedGlyphNode[] =
  normSharedNodes.length > 0 ? normSharedNodes : (props.nodes as ExtendedGlyphNode[]);

const links: Link[] =
  normSharedLinks.length > 0 ? normSharedLinks : (props.links as Link[]);

// If you want beams, do the same (or keep your local loader/state)
const effectiveBeams = (sharedBeams ?? []).length > 0 ? sharedBeams : beams;

// (optional) flag to know if we’re in fallback mode
const useFallback = normSharedNodes.length === 0 && normSharedLinks.length === 0;

// 4) Merge predicted — ExtendedGlyphNode extends GlyphNode, so it's assignable.
// If TS still complains, cast to GlyphNode[] explicitly.
const { mergedNodes, mergedLinks } = useMemo(
  () =>
    mergePredictedGraphLocal({
      nodes: nodes as unknown as GlyphNode[],
      links,
      tickFilter,
      showCollapsed,
      // predictedNodes: qfcData?.predictedNodes ?? [],
      // predictedLinks: qfcData?.predictedLinks ?? [],
    }),
  [nodes, links, tickFilter, showCollapsed]
);

  // 4) Orbit helper — build once per nodes list
  const setOrbitTargetToGlyph = useMemo(
    () => setOrbitTargetToGlyphFactory({ nodes, cameraRef, controlsRef }),
    [nodes]
  );

  // 5) Center-by-glyph helper (uses merged graph)
  const centerToGlyph = useMemo(
    () =>
      centerToGlyphFactory({
        mergedNodes,
        setObserverPosition,
        setOrbitTargetToGlyph,
      }),
    [mergedNodes, setObserverPosition, setOrbitTargetToGlyph]
  );

  // 5b) Global focus→center hook (window event)
  useEffect(() => {
    const onFocus = (e: any) => {
      const id = e?.detail?.glyphId ?? e?.detail?.id;
      if (!id) return;
      try {
        centerToGlyph(id);
      } catch {
        /* no-op */
      }
    };
    window.addEventListener("focus_glyph", onFocus);
    return () => window.removeEventListener("focus_glyph", onFocus);
  }, [centerToGlyph]);

// 6) QWave beams JSX
const qwaveBeams = useMemo(
  () =>
    renderQWaveBeamsLocal({
      beamData: beamData ?? [],
      setSelectedBeam,
    }),
  [beamData, setSelectedBeam]
);

const specialOps = useMemo(() => new Set(["⧖", "↔", "⬁", "🧬", "🪞"]), []);
const [focusedNode, setFocusedNode] = useState<string | null>(null);

// Merge base props with live graph adds from QFC events
const liveNodes = useMemo<ExtendedGlyphNode[]>(
  () => [...(props.nodes || []), ...(graphAdds.nodes as ExtendedGlyphNode[])],
  [props.nodes, graphAdds.nodes]
);
const liveLinks = useMemo<Link[]>(
  () => [...(props.links || []), ...(graphAdds.links as Link[])],
  [props.links, graphAdds.links]
);

// ─────────────────────────────────────────────────────────────
// STEP 5A–5C: Collaboration presence (INSIDE component)
// ─────────────────────────────────────────────────────────────

// 5A) Push viewport (camera target + a simple "zoom") on OrbitControls changes
const lastViewportSent = useRef<number>(0);

const handleOrbitChange = useCallback(() => {
  if (!controlsRef.current || !cameraRef.current || !applyOp?.setViewport) return;

  const now = Date.now();
  if (now - lastViewportSent.current < 150) return; // throttle ~6/s
  lastViewportSent.current = now;

  const t = controlsRef.current.target as THREE.Vector3;
  const cam = cameraRef.current;
  const zoom = cam.position.distanceTo(new THREE.Vector3(t.x, t.y, t.z));

  applyOp.setViewport([t.x, t.y, t.z], zoom);
}, [applyOp]);

// 5B) Push live cursor position into presence
useEffect(() => {
  if (!applyOp?.setCursor) return;
  const onMove = (e: MouseEvent) => applyOp.setCursor(e.clientX, e.clientY);
  window.addEventListener("mousemove", onMove);
  return () => window.removeEventListener("mousemove", onMove);
}, [applyOp]);

// 5C) Helper to push current glyph selection into presence (call this from your selection logic)
const selectGlyph = useCallback((ids: Array<string | number>) => {
  if (!applyOp?.setSelection) return;
  applyOp.setSelection(ids.map(String)); // normalize ids
}, [applyOp]);

// Decide which container to subscribe to (derive from nodes, or fall back)
const socketContainerId = useMemo(() => {
  const fromNodes = (props.nodes || []).find(n => !!n.containerId)?.containerId;
  return (fromNodes || (props as any).containerId || "ucs_hub") as string;
}, [props.nodes]);

// Subscribe to QFC websocket updates (single top-level hook; no conditionals)
useQfcSocket(socketContainerId, (payload: { nodes?: any[]; links?: any[] }) => {
  setGraphAdds(prev => ({
    nodes: [...prev.nodes, ...(payload?.nodes ?? [])],
    links: [...prev.links, ...(payload?.links ?? [])],
  }));
});

// Example fetch — keep your existing demo injection
useEffect(() => {
  fetch("/api/test-mixed-beams")
    .then((res) => res.json())
    .then((data) => {
      // feed your renderer; if it expects `beamData`, set that
      setBeamData(data?.beams || []);
    })
    .catch(() => void 0);
}, []);

// 🎬 Replay playback loop
useEffect(() => {
  if (!isReplaying) return;
  const interval = setInterval(() => {
    setPlaybackIndex((prev) => {
      if (prev >= replayFrames.length - 1) {
        clearInterval(interval);
        setIsReplaying(false);
        return prev;
      }
      return prev + 1;
    });
  }, 100); // ⏱️ 100ms per frame
  return () => clearInterval(interval);
}, [isReplaying, replayFrames]);

const handleRetryFromBranch = async () => {
  try {
    const res = await fetch("/api/mutate_from_branch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trailId: selectedBranch }),
    });
    const result = await res.json();
    // 🔁 Push new glyphs/beams into QFC live (via window event shim)
    broadcast_qfc_update(result);
  } catch (e) {
    console.warn("Retry from branch failed:", e);
  }
};

const handleDroppedScroll = async (glyph: string, scroll: string) => {
  try {
    const response = await fetch("/api/inject_scroll", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ glyph, scroll }),
    });
    const result = await response.json();

    // ⬆️ Inject response into QFC field live
    if (result && result.glyphs) {
      broadcast_qfc_update(result); // 🚀 Inject into QFC
      setOrbitTargetToGlyph(glyph); // 🎯 Center to glyph

      // 🎥 Capture current frame after successful scroll injection
      const frame = {
        timestamp: Date.now(),
        glyphs: liveNodes,
        links: liveLinks,
        observer: observerPosition,
        branch: selectedBranch,
        scrolls: [{ glyph, scroll }],
      };
      setReplayFrames((prev) => [...prev, frame]);
    } else {
      console.warn("⚠️ No glyphs returned from scroll injection");
    }
  } catch (err) {
    console.error("❌ Scroll injection failed:", err);
  }
};

// ─────────────────────────────────────────────────────────────
// 🔌 Window-event shim so `broadcast_qfc_update(...)` keeps working
//    (No direct `qfc` object; the websocket subscription is above.)
// ─────────────────────────────────────────────────────────────
useEffect(() => {
  const onForkBeam = (e: any) => {
    const p = e?.detail ?? {};
    const id = p.wave_id ?? crypto.randomUUID();
    setBeams(prev =>
      prev.some((b: any) => b?.id === id) ? prev : [{ id, ...p }, ...prev].slice(0, 200)
    );
  };

  const onIndex = (_e: any) => {
    // HUD/metrics updates welcome here if desired
  };

  const onQfc = (e: any) => {
    const p = e?.detail ?? {};
    setGraphAdds(prev => ({
      nodes: [...prev.nodes, ...(p.nodes ?? [])],
      links: [...prev.links, ...(p.links ?? [])],
    }));
  };

  window.addEventListener("glyphwave.fork_beam", onForkBeam as any);
  window.addEventListener("index_update", onIndex as any);
  window.addEventListener("qfc_update", onQfc as any);

  return () => {
    window.removeEventListener("glyphwave.fork_beam", onForkBeam as any);
    window.removeEventListener("index_update", onIndex as any);
    window.removeEventListener("qfc_update", onQfc as any);
  };
}, []);

  // Listen to local/window rebroadcasts (from our shim or other parts of the app)
  useEffect(() => {
    const onQfc = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      setGraphAdds((g) => ({
        nodes: [...(g.nodes || []), ...(detail?.nodes || [])],
        links: [...(g.links || []), ...(detail?.links || [])],
      }));
    };
    window.addEventListener("qfc_update", onQfc as any);
    return () => window.removeEventListener("qfc_update", onQfc as any);
  }, []);

  // ─────────────────────────────────────────────────────────────

  return (
    <div
      className="relative w-full h-full"
      onDrop={(e) => {
        e.preventDefault();
        const data = e.dataTransfer.getData("application/glyph-scroll");
        if (data) {
          const { glyph, scroll } = JSON.parse(data);
          handleDroppedScroll(glyph, scroll);
        }
      }}
      onDragOver={(e) => e.preventDefault()}
    >
      {/* 🎛️ Controls Panel */}
      <div className="absolute top-4 left-4 z-50 space-y-2 pointer-events-auto">
        <div className="flex gap-2">
          <Button
            className="text-xs px-3 py-1 h-8 bg-blue-900 hover:bg-blue-800"
            onClick={() => setShowPredictedLayer((v) => !v)}
          >
            🔮 {showPredictedLayer ? "Hide" : "Show"} Predicted Layer
          </Button>
          <Button
            className="text-xs px-3 py-1 h-8 bg-purple-700 hover:bg-purple-600"
            onClick={() => setSplitScreen((v) => !v)}
          >
            🧠 {splitScreen ? "Unsplit View" : "Split Reality / Dream"}
          </Button>
          <Button
            className="text-xs px-3 py-1 h-8 bg-slate-700 hover:bg-slate-600"
            onClick={() => setPredictedMode((v) => !v)}
          >
            🌓 {predictedMode ? "Normal" : "Fade Real Nodes"}
          </Button>
          <Button
            className="text-xs px-3 py-1 h-8 bg-sky-900 hover:bg-sky-800"
            onClick={() => setPredictedOverlay((v) => !v)}
          >
            🌐 {predictedOverlay ? "Hide Overlay" : "Show Overlay"}
          </Button>
          <Button
            className="text-xs px-3 py-1 h-8 bg-emerald-700 hover:bg-emerald-600"
            onClick={handleRetryFromBranch}
          >
            ♻️ Retry From Branch
          </Button>
        </div>
      </div>

      {/* 🧠 Canvas + Scene */}
      <Canvas
        camera={{ fov: 60, position: [0, 0, 6] }}
        onCreated={({ camera }) => {
          cameraRef.current = camera as THREE.PerspectiveCamera;
        }}
      >
        <ambientLight intensity={0.9} />
        <directionalLight position={[5, 10, 7]} intensity={0.6} />
        <OrbitControls ref={controlsRef} />

        {/* Nodes */}
        {liveNodes?.map((n) => (
          <Node
            key={(n as any).id ?? `${n.position.join(",")}`}
            node={n}
            onTeleport={props.onTeleport}
          />
        ))}

        {/* Links */}
        {liveLinks?.map((l, idx) => {
          const a = liveNodes.find((n) => (n as any).id === l.source);
          const b = liveNodes.find((n) => (n as any).id === l.target);
          if (!a || !b) return null;

          const points = [
            new THREE.Vector3(...a.position),
            new THREE.Vector3(...b.position),
          ];

          return (
            <line key={`link-${idx}`}>
              <bufferGeometry>
                <bufferAttribute
                  attach="attributes-position"
                  count={points.length}
                  array={new Float32Array(points.flatMap((p) => [p.x, p.y, p.z]))}
                  itemSize={3}
                />
              </bufferGeometry>
              <lineBasicMaterial color={getLinkColor(l.type)} linewidth={1} />
            </line>
          );
        })}

        {/* (Optional) Beams in 3D space if your renderer expects it */}
        {beams?.map((b, idx) => (
          <QWaveBeam key={`beam-${idx}`} {...(b as BeamProps)} />
        ))}
      </Canvas>

      {/* ═══ Overlays & HUD (non-3D DOM layers) ═══ */}

      {/* Emotion overlay over current nodes */}
      <EmotionOverlay nodes={liveNodes as any} />

      {/* Predicted Layer Overdraw */}
      {showPredictedLayer && props.predictedOverlay && (
        <PredictedLayerRenderer
          {...({
            nodes: (props.predictedOverlay.nodes || []) as any,
            links: (props.predictedOverlay.links || []) as any,
            fadedRealMode: predictedMode, // keep your original semantic
            visible: true,                // harmless extra for variants that use it
          } as any)}
        />
      )}

      {/* Split reality/dream zoom (pass full scene) */}
      {splitScreen && (
        <ClusterZoomRenderer
          {...({
            nodes: liveNodes as any,
            links: liveLinks as any, // tolerated via cast; ignored if not used
            radius: 2.5,
            onZoomed: (ids: string[]) => console.log("🔍 Zoomed cluster:", ids),
          } as any)}
        />
      )}

      {/* Replay HUD */}
      <ScrollReplayOverlay
        {...({
          isReplaying,
          frames: replayFrames,
          playbackIndex,
          onPlay: () => setIsReplaying(true),
          onPause: () => setIsReplaying(false),
          onSeek: setPlaybackIndex,
          visible: isReplaying, // supports simpler variant too
        } as any)}
      />

      {/* Strategy / Branch chooser */}
      <StrategyOverlay
        {...({
          branches: availableBranches,
          selected: selectedBranch,
          onSelect: setSelectedBranch,
          visible: true,
        } as any)}
      />

      {/* Observer direction mini-view */}
      <ObserverViewport
        {...({
          position: observerPosition,
          direction: observerDirection,
          enabled: true,
        } as any)}
      />

      {/* Memory scroll list / timeline */}
      <MemoryScroller
        {...({
          frames: replayFrames,
          onJump: (idx: number) => setPlaybackIndex(idx),
          active: isReplaying,
        } as any)}
      />

      {/* Hover mutation + trails */}
      <HoverMutationTrace {...({ beam: selectedBeam } as any)} />
      <MultiNodeCollapseTrail
        {...({ segments: collapseTrails, visible: true } as any)}
      />
      <BreakthroughDeadendTrail
        {...({
          segments: deadendTrails,
          visible: true,
        } as any)}
      />
      <HolographicCausalityTrails
        {...({
          // your version used `segments`; some builds want `trails`
          segments: [...(collapseTrails as any[]), ...(breakthroughTrails as any[])],
          trails: collapseTrails as any,
        } as any)}
      />

      {/* Logic overlay for an active beam */}
      <BeamLogicOverlay {...({ beam: selectedBeam } as any)} />

      {/* QWave preview side panel (uses beams list) */}
      <div className="absolute right-2 top-2 max-w-sm">
        <QWavePreviewPanel
          {...({
            beams: beams as any,
            onSelect: setSelectedBeam,
            selectedBeamId: (selectedBeam as any)?.id,
            beamMetadata: (selectedBeam as any)?.qwave,
          } as any)}
        />
      </div>
    </div>
  );
}

// 🌐 Glyph Node Component
const Node = ({
  node,
  onTeleport,
}: {
  node: ExtendedGlyphNode;
  onTeleport?: (id: string) => void;
}) => {
  const ref = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const pulseRef = useRef(0);

  useFrame(() => {
    if (ref.current) {
      if (node.predicted) {
        pulseRef.current += 0.05;
        const scale = 1 + 0.1 * Math.sin(pulseRef.current);
        ref.current.scale.set(scale, scale, scale);
      }
      if (hovered) {
        ref.current.rotation.y += 0.01;
      }
    }
  });

  return (
    <mesh
      ref={ref}
      position={node.position}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
      onClick={() => node.containerId && onTeleport?.(node.containerId!)}
    >
      <sphereGeometry args={[0.3, 32, 32]} />
      <meshStandardMaterial
        color={
          node.locked
            ? "#ff3333"
            : node.color || (node.predicted ? "#00ffff" : "#ffffff")
        }
        emissive={
          node.locked ? "#ff3333" : node.predicted ? "#00ffff" : "#000000"
        }
        emissiveIntensity={node.locked ? 2.0 : node.predicted ? 1.5 : 0}
      />

      {/* 🟢 Emotion Pulse Overlay */}
      {node.emotion && (
        <>
          <MeshEmotionPulse node={node as any} />
          <HtmlEmotionPulse node={node as any} />
        </>
      )}

      {/* 🏷️ Label UI */}
      <Html>
        <Card className="p-2 rounded-xl shadow-lg text-xs text-center bg-white/80 backdrop-blur">
          {(node as any).label ?? "•"}
        </Card>
      </Html>

      {/* 🔒 Floating lock */}
      {node.locked && (
        <Html position={[node.position[0], node.position[1] + 1.5, node.position[2]]}>
          <div className="text-2xl text-red-500 font-bold drop-shadow">🔒</div>
        </Html>
      )}
    </mesh>
  );
};

// 🔗 Visual Link Line Component
const LinkLine: React.FC<{
  source: GlyphNode;
  target: GlyphNode;
  type?: string;
  isDream?: boolean;
}> = ({ source, target, type, isDream = false }) => {
  const points = [
    new THREE.Vector3(...source.position),
    new THREE.Vector3(...target.position),
  ];
  const geometry = new THREE.BufferGeometry().setFromPoints(points);

  return (
    <line>
      <primitive object={geometry} attach="geometry" />
      <lineBasicMaterial
        attach="material"
        color={isDream ? "#d946ef" : "#888"}
        linewidth={1}
        transparent
        opacity={isDream ? 0.4 : 1}
      />
    </line>
  );
};

// 💠 ReplayPulse Overlay for Entangled/Predicted Nodes
export const ReplayPulse: React.FC<{ position: [number, number, number] }> = ({ position }) => {
  const pulseRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    const scale = 1 + Math.sin(clock.getElapsedTime() * 4) * 0.2;
    if (pulseRef.current) {
      pulseRef.current.scale.set(scale, scale, scale);
    }
  });

  return (
    <mesh position={position} ref={pulseRef}>
      <ringGeometry args={[0.5, 0.6, 32]} />
      <meshBasicMaterial color="#00ffcc" transparent opacity={0.6} />
    </mesh>
  );
};

/* ────────────────────────────────────────────────────────────────────────────
   Pure helpers you can call FROM INSIDE your main component so we don’t
   reference component-scoped variables at module scope. This eliminates the
   “Cannot find name 'nodes' / 'cameraRef' / …” TS errors without losing logic.
   ──────────────────────────────────────────────────────────────────────────── */

/** ─────────────────────────────────────────────────────────────
 *  Local, non-exported helpers (avoid duplicate symbol errors)
 *  ─────────────────────────────────────────────────────────────
 */

/** Safe getter bound to a nodes array */
const getNodeByIdLocal = (nodes: GlyphNode[], id: string) =>
  nodes.find((n) => (n as any).id === id);

/** Load mixed test beams (original /api/test-mixed-beams fetch) */
function useLoadQWaveBeamsLocal(
  setBeamData: React.Dispatch<React.SetStateAction<any[] | null>>
) {
  useEffect(() => {
    let alive = true;
    fetch("/api/test-mixed-beams")
      .then((res) => res.json())
      .then((data) => alive && setBeamData(data))
      .catch(() => void 0);
    return () => {
      alive = false;
    };
  }, [setBeamData]);
}

/** Your static trails, returned so you can use them inline */
function getStaticTrailsLocal() {
  const collapseTrails = [
    {
      id: "trail-1",
      path: [
        [0, 0, 0],
        [1, 2, 0],
        [2, 4, 0],
      ] as [number, number, number][],
      color: "#ffaa00",
    },
  ];

  const breakthroughTrails = [
    {
      points: [
        [0, 0, 0],
        [1.5, 0.5, 0],
        [2.2, 1.2, 0],
      ] as [number, number, number][],
      type: "breakthrough",
    },
  ];

  const deadendTrails = [
    {
      points: [
        [1, -1, 0],
        [1.5, -1.5, 0],
        [2.0, -2.0, 0],
      ] as [number, number, number][],
      type: "deadend",
    },
  ];

  return { collapseTrails, breakthroughTrails, deadendTrails };
}

/** Merge predicted nodes/links into the main graph (preserves your behavior) */
function mergePredictedGraphLocal(params: {
  nodes: GlyphNode[];
  links: { source: string; target: string; tick?: number }[];
  tickFilter?: number;
  showCollapsed?: boolean;
  predictedNodes?: GlyphNode[];
  predictedLinks?: { source: string; target: string; tick?: number }[];
}) {
  const {
    nodes,
    links,
    tickFilter,
    showCollapsed = true,
    predictedNodes = [],
    predictedLinks = [],
  } = params;

  const mergedNodes: GlyphNode[] = [
    ...nodes.filter((node) => {
      const matchTick = tickFilter === undefined || (node as any).tick === tickFilter;
      const matchCollapse =
        showCollapsed || (node as any).collapse_state !== "collapsed";
      return matchTick && matchCollapse;
    }),
    ...predictedNodes
      .filter((pn) => !nodes.some((n) => (n as any).id === (pn as any).id))
      .map((pn) => ({ ...(pn as any), isDream: true as const })),
  ];

  const mergedLinks = [
    ...links.filter((link) => tickFilter === undefined || link.tick === tickFilter),
    ...predictedLinks
      .filter((pl) => !links.some((l) => l.source === pl.source && l.target === pl.target))
      .map((pl) => ({ ...pl, isDream: true as const })),
  ];

  return { mergedNodes, mergedLinks };
}

/** Render QWave beams with logic overlays (keeps your mapping, but type-safe via casts) */
function renderQWaveBeamsLocal(params: {
  beamData: any[] | null;
  setSelectedBeam: React.Dispatch<React.SetStateAction<any | null>>;
}) {
  const { beamData, setSelectedBeam } = params;

  return (beamData || [])
    .filter((beam) => (beam as any).source && (beam as any).target)
    .map((b: any) => {
      const {
        source,
        target,
        qwave,
        id,
        predicted,
        collapse_state,
        sqiScore,
      } = b;

      const hasLogicPacket = qwave?.logic_packet;
      const midPosition: [number, number, number] = [
        (source[0] + target[0]) / 2,
        (source[1] + target[1]) / 2,
        (source[2] + target[2]) / 2,
      ];

      return (
        <React.Fragment key={`beam-${id ?? `${source}-${target}`}`}>
          <group
            onClick={() =>
              setSelectedBeam({
                source,
                target,
                qwave,
                id,
                predicted,
                collapse_state,
                sqiScore,
              })
            }
          >
            <QWaveBeam
              source={source as [number, number, number]}
              target={target as [number, number, number]}
              prediction={predicted}
              collapseState={collapse_state}
              sqiScore={sqiScore || 0}
              show={true}
            />
          </group>

          {hasLogicPacket && (
            <BeamLogicOverlay
              position={midPosition}
              packet={qwave.logic_packet}
              visible={true}
            />
          )}
        </React.Fragment>
      );
    });
}

/** Center by glyph id using merged nodes (uses your already-declared orbit helper) */
function mkCenterToGlyph(opts: {
  mergedNodes: GlyphNode[];
  setObserverPosition: React.Dispatch<React.SetStateAction<[number, number, number]>>;
  setOrbitTargetToGlyph: (glyphId: string) => void;
}) {
  const { mergedNodes, setObserverPosition, setOrbitTargetToGlyph } = opts;
  return (glyph: string) => {
    const node =
      mergedNodes.find((n) => (n as any).glyph === glyph || (n as any).id === glyph);
    if (node) {
      console.log("🎯 Centering to glyph node:", glyph, (node as any).position);
      setObserverPosition(((node as any).position || [0, 0, 0]) as [number, number, number]);
      // Prefer id if present, otherwise use glyph string
      const id = (node as any).id ?? glyph;
      setOrbitTargetToGlyph(String(id));
    } else {
      console.warn("❌ Glyph not found in nodes:", glyph);
    }
  };
}

/** Render a captured replay frame (nodes + links) – factory captures scope */
function makeRenderReplayFrame(
  nodes: GlyphNode[],
  onTeleport?: (id: string) => void
) {
  // local, type-safe finder
  const find = (id: string) => nodes.find((n) => String(n.id) === String(id));

  return (frame: any) => (
    <>
      {(frame?.glyphs ?? []).map((node: any, idx: number) => (
        <Node key={`replay-node-${node?.id ?? idx}`} node={node} onTeleport={onTeleport} />
      ))}

      {(frame?.links ?? []).map((link: any, idx: number) => {
        const s = find(String(link?.source));
        const t = find(String(link?.target));
        if (!s || !t) return null;
        return (
          <LinkLine
            key={`replay-link-${idx}`}
            source={s as any}
            target={t as any}
            type={link?.type}
            isDream={Boolean(link?.isDream)}
          />
        );
      })}
    </>
  );
}

/** Minimal, dependency-free trail renderer for replay links */
const ReplayBeamTrails: React.FC<{ frames: any[]; index: number }> = ({
  frames,
  index,
}) => {
  type Pt = [number, number, number];

  const frame = Array.isArray(frames) ? frames[index] : undefined;
  const links: any[] = Array.isArray(frame?.links) ? frame!.links : [];
  if (!links.length) return null;

  const toPoints = (trail: any): Pt[] =>
    Array.isArray(trail?.points)
      ? (trail.points as Pt[])
      : Array.isArray(trail)
      ? (trail as Pt[])
      : [];

  const colorFor = (t?: string) =>
    t === "breakthrough"
      ? "#22c55e"
      : t === "deadend"
      ? "#ef4444"
      : t === "collapsed"
      ? "#94a3b8"
      : "#f59e0b";

  return (
    <>
      {links.map((lnk: any, i: number) => {
        const pts = toPoints(lnk?.trail);
        if (!pts.length) return null;

        const geom = new THREE.BufferGeometry().setFromPoints(
          pts.map(([x, y, z]) => new THREE.Vector3(x, y, z))
        );

        return (
          <line key={`replay-trail-${i}`}>
            <primitive object={geom} attach="geometry" />
            <lineBasicMaterial
              attach="material"
              color={colorFor(lnk?.collapseState)}
              transparent
              opacity={0.85}
            />
          </line>
        );
      })}
    </>
  );
}; // <-- helper ends here. Do NOT put another "return (" after this line.

// ── Render (inside QuantumFieldCanvas) ──
return (
  <>
    {/* 🧠 Render QWave Beams */}
    {qwaveBeams}

    {/* 🌀 Replay Beam Trails */}
    {isReplaying ? (
      <ReplayBeamTrails frames={replayFrames} index={playbackIndex} />
    ) : null}

    {/* 🔘 HUD Controls */}
    <div className="absolute top-4 left-4 z-50 space-y-2">
      <Button
        className="text-xs px-3 py-1 h-8 bg-blue-900 hover:bg-blue-800"
        onClick={() => setShowPredictedLayer(!showPredictedLayer)}
      >
        🔮 {showPredictedLayer ? "Hide" : "Show"} Predicted Layer
      </Button>
      <Button
        className="text-xs px-3 py-1 h-8 bg-purple-700 hover:bg-purple-600"
        onClick={() => setSplitScreen(!splitScreen)}
      >
        🧠 {splitScreen ? "Unsplit View" : "Split Reality / Dream"}
      </Button>
      <Button
        className="text-xs px-3 py-1 h-8 bg-green-900 hover:bg-green-800"
        onClick={() => setIsReplaying(!isReplaying)}
      >
        {isReplaying ? "⏸ Pause Replay" : "▶️ Start Replay"}
      </Button>
      <Button
        className="text-xs px-3 py-1 h-8 bg-slate-700 hover:bg-slate-600"
        onClick={() => setPredictedMode(!predictedMode)}
      >
        🌓 {predictedMode ? "Normal" : "Fade Real Nodes"}
      </Button>
      <Button
        className="text-xs px-3 py-1 h-8 bg-sky-900 hover:bg-sky-800"
        onClick={() => setPredictedOverlay(!predictedOverlay)}
      >
        🌐 {predictedOverlay ? "Hide Overlay" : "Show Overlay"}
      </Button>
    </div>

    {isReplaying && replayFrames[playbackIndex] && (
      <div className="absolute top-4 right-4 text-xs bg-black/70 text-white p-2 rounded z-50">
        ⏪ Replaying Frame #{playbackIndex}
      </div>
    )}

    {/* 🔁 Branch Selection + Retry */}
    <div className="absolute top-4 right-4 z-50 w-64">
      <ReplayBranchSelector
        availableBranches={availableBranches}
        selectedBranch={selectedBranch}
        onSelect={setSelectedBranch}
        onRetry={handleRetryFromBranch}
      />
    </div>

    {/* 🧠 Canvas Views */}
    <div className="h-full w-full relative flex">
      {splitScreen ? (
        // 🟢 Split View: Real vs Dream
        <div className="w-1/2 h-full border-r border-slate-700">
          <Canvas
            camera={{ position: [0, 0, 10], fov: 50 }}
            onCreated={({ camera }) => {
              cameraRef.current = camera;
            }}
          >
            <ambientLight intensity={0.7} />
            <pointLight position={[10, 10, 10]} />
            <OrbitControls
              ref={controlsRef}
              enableZoom
              enablePan
              enableRotate
              target={new THREE.Vector3(...observerPosition)}
            />

            {/* 🌐 Symbolic QWave Beams */}
            {beamData?.map((beam: any, idx: number) => (
              <group key={idx} onClick={() => setSelectedBeam(beam)}>
                <QWaveBeam {...beam} />
              </group>
            ))}

            {/* 🌈 Nodes (Real + Dream) */}
            {isReplaying && replayFrames[playbackIndex] && (
              <>{renderReplayFrame(replayFrames[playbackIndex])}</>
            )}

            {mergedNodes.map((node) => {
              const inView = isInObserverView(
                node.position,
                observerPosition,
                observerDirection
              );

              return (
                <React.Fragment key={node.id}>
                  {(node.source === "dream" || (node as any).isDream) && (
                    <mesh position={node.position}>
                      <ringGeometry args={[0.6, 0.75, 32]} />
                      <meshBasicMaterial
                        color="#d946ef"
                        transparent
                        opacity={0.75}
                      />
                    </mesh>
                  )}

                  <Node
                    node={node}
                    onTeleport={onTeleport}
                    highlight={inView}
                    className={
                      (node as any).glyph === focusedNode
                        ? "ring-2 ring-green-400 scale-110"
                        : ""
                    }
                  />

                  {/* ✨ Entropy Overlay */}
                  {typeof (node as any).entropy === "number" && (
                    <EntropyNode
                      position={node.position}
                      entropy={(node as any).entropy}
                      nodeId={node.id}
                    />
                  )}

                  {/* 🧠 Hover Memory Summary */}
                  {(node as any).memoryTrace && (
                    <HoverMemorySummary
                      position={[
                        node.position[0],
                        node.position[1] + 1.5,
                        node.position[2],
                      ]}
                      summary={(node as any).memoryTrace.summary}
                      containerId={(node as any).memoryTrace.containerId}
                      agentId={(node as any).memoryTrace.agentId}
                    />
                  )}
                </React.Fragment>
              );
            })}

            {/* 🔗 Merged Links (Real + Dream) */}
            {mergedLinks.map((link, i) => {
              const source = getNodeById(link.source);
              const target = getNodeById(link.target);
              if (!source || !target) return null;
              return (
                <LinkLine
                  key={`link-${i}`}
                  source={source}
                  target={target}
                  type={link.type}
                  isDream={Boolean((link as any).isDream)}
                />
              );
            })}

            {/* 🔮 Predicted Layer Overlay */}
            {showPredictedLayer && (
              <PredictedLayerRenderer
                nodes={[]}
                links={[]}
              />
            )}

            {/* 💫 Optional HUD Layers */}
            <EmotionOverlay visible={emotionOverlayEnabled} />
            <ScrollReplayOverlay visible={scrollReplayActive} />
            <StrategyOverlay visible={strategyOverlayEnabled} />
            <ObserverViewport enabled={observerMode} />
            <MemoryScroller active={memoryScrollerActive} />
          </Canvas>
        </div>
      ) : (
        // 🔁 Default Unified View
        <Canvas camera={{ position: [0, 0, 10], fov: 50 }}>
          <ambientLight intensity={0.7} />
          <pointLight position={[10, 10, 10]} />
          <OrbitControls
            enableZoom
            enablePan
            enableRotate
            target={new THREE.Vector3(...observerPosition)}
          />

          {/* 🔮 Predicted Overlay */}
          {showPredictedLayer && (
            <PredictedLayerRenderer nodes={[]} links={[]} visible={true} />
          )}

          {/* 🔗 Links */}
          {mergedLinks.map((link, i) => {
            const source = getNodeById(link.source);
            const target = getNodeById(link.target);
            if (!source || !target) return null;
            return (
              <LinkLine
                key={`link-${i}`}
                source={source}
                target={target}
                type={link.type}
                isDream={Boolean((link as any).isDream)}
              />
            );
          })}
        </Canvas>
      )}
    </div>
    {/* end of split-screen vs unified switch */}

    {/* 💫 Render QWaveBeams between nodes (mergedLinks) */}
    {mergedLinks.map((link, i) => {
      const source = getNodeById(link.source);
      const target = getNodeById(link.target);
      if (!source || !target) return null;

      return (
        <group key={`beam-${i}`} onClick={() => setSelectedBeam(link)}>
          <QWaveBeam
            source={source.position}
            target={target.position}
            prediction={Boolean((source as any).predicted || (target as any).predicted)}
            collapseState={(source as any).collapse_state || (target as any).collapse_state}
            sqiScore={
              (source as any).goalMatchScore ??
              (source as any).rewriteSuccessProb ??
              (target as any).goalMatchScore ??
              (target as any).rewriteSuccessProb ??
              0
            }
            show={true}
          />
        </group>
      );
    })}

    {/* 🌈 Glyph Nodes from beamData */}
    {beamData?.glyphs?.map((glyph: any) => (
      <React.Fragment key={`beam-glyph-${glyph.id}`}>
        <Node node={glyph} onTeleport={onTeleport} />
        {specialOps.has(glyph.value) && glyph.type === "operator" && (
          <HighlightedOperator value={glyph.value} position={glyph.position} />
        )}
      </React.Fragment>
    ))}

{/* 🚀 Mixed Beams with rerouted paths */}
{beamData?.beams?.map((beam: any) => {
  const { id, source, target, predicted, collapse_state, sqiScore } = beam;
  const focusPoint = observerPosition; // use current observer as focus anchor
  const reroutedPath = rerouteBeam(source, target, focusPoint);

  return (
    <QWaveBeam
      key={`mixed-beam-${id}`}
      path={reroutedPath}
      prediction={predicted}
      collapseState={collapse_state}
      sqiScore={sqiScore || 0}
      show={true}
    />
  );
})}

{/* ⚛ Filtered Node Rendering */}
{(filteredNodes ?? mergedNodes).map((node) => (
  <React.Fragment key={node.id}>
    {/* 🧠 Node */}
    <Node node={node} onTeleport={onTeleport} />

    {/* 🔒 SoulLaw Lock */}
    {node.locked && (
      <Html
        position={[
          node.position[0],
          node.position[1] + 1.5,
          node.position[2],
        ]}
      >
        <div className="text-2xl text-red-500 font-bold drop-shadow">🔒</div>
      </Html>
    )}

    {/* 🎨 Entropy Overlay */}
    {typeof (node as any).entropy === "number" && (
      <EntropyNode
        position={node.position}
        entropy={(node as any).entropy}
        nodeId={node.id}
      />
    )}

    {/* 🧠 Memory Trace Hover */}
    {(node as any).memoryTrace && (
      <HoverAgentLogicView
        position={[
          node.position[0],
          node.position[1] + 1.2,
          node.position[2],
        ]}
        logicSummary={(node as any).memoryTrace.summary}
        containerId={(node as any).memoryTrace.containerId}
        agentId={(node as any).memoryTrace.agentId}
      />
    )}

    {/* ➕ Spawn Container Button */}
    <Html
      position={[
        node.position[0] + 0.8,
        node.position[1] + 1.2,
        node.position[2],
      ]}
    >
      <button
        className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white px-2 py-1 rounded shadow"
        onClick={async () => {
          try {
            const res = await fetch("/api/spawn_container_from_node", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ nodeId: node.id }),
            });
            const data = await res.json();
            if (data.success && data.newContainerId) {
              alert(`✅ Container spawned: ${data.newContainerId}`);
            } else {
              alert("⚠️ Failed to spawn container.");
            }
          } catch (err) {
            alert("🚨 Spawn failed: " + err);
          }
        }}
      >
        ➕ Spawn
      </button>
    </Html>
  </React.Fragment>
))}

{/* 🔍 Zoom Highlights */}
<ClusterZoomRenderer
  nodes={filteredNodes ?? mergedNodes}
  radius={2.5}
  onZoomed={(ids) => console.log("🔍 Zoomed cluster:", ids)}
/>

{/* 🧠 Collapse + Causality Trails */}
<TraceCollapseRenderer trails={collapseTrails} color="#ffaa00" />
<HoverMutationTrace
  trails={hoverMutationTrails ?? []}
  hoveredNodeId={hoveredNode?.id}
/>
<HolographicCausalityTrails trails={causalitySegments ?? []} />
<BreakthroughDeadendTrail
  segments={[...(breakthroughTrails || []), ...(deadendTrails || [])]}
  visible={true}
/>
<MultiNodeCollapseTrail
  segments={multiCollapseTrails ?? []}
  visible={true}
/>

{/* 🔬 QWave Preview Panel */}
{selectedBeam?.id && (
  <QWavePreviewPanel
    selectedBeamId={selectedBeam.id}
    beamMetadata={selectedBeam.qwave}
  />
)}

{/* 🌐 Predicted Overlay (Real View) */}
{predictedOverlay && (
  <PredictedLayerRenderer
    nodes={qfcData?.predictedNodes || []}
    links={qfcData?.predictedLinks || []}
    visible={true}
  />
)}

{/* 🔮 Dream QFC Canvas (Right side) */}
<div className="w-1/2 h-full">
  <Canvas camera={{ position: [0, 0, 10], fov: 50 }}>
    <ambientLight intensity={0.5} />
    <pointLight position={[5, 5, 5]} />
    <OrbitControls
      enableZoom
      enablePan
      enableRotate
      target={new THREE.Vector3(...observerPosition)}
    />

    {/* 🔮 Predicted Layer */}
    <PredictedLayerRenderer
      nodes={qfcData?.predictedNodes || []}
      links={qfcData?.predictedLinks || []}
      visible={true}
    />

    {/* 💫 Dream Visual Layers */}
    <EmotionOverlay visible={!!emotionOverlayEnabled} />
    <ScrollReplayOverlay visible={!!scrollReplayActive} />
    <StrategyOverlay visible={!!strategyOverlayEnabled} />
    <ObserverViewport enabled={!!observerMode} />
    <MemoryScroller active={!!memoryScrollerActive} />
  </Canvas>
</div>
{/* End of right-side canvas */}

{/* 📤 Collapse Timeline Export + Tick Info Panel */}
<div
  className="absolute top-4 right-4 text-xs text-white bg-black/70 rounded-md p-2 z-50 space-y-2"
  role="region"
  aria-label="collapse-export"
>
  <div>
    🕓 Tick Filter: <strong>{tickFilter ?? "—"}</strong>
  </div>

  <div>
    📉 Collapsed Nodes:{" "}
    <strong>
      {(nodes ?? []).reduce(
        (acc: number, n: any) => acc + (n?.collapse_state === "collapsed" ? 1 : 0),
        0
      )}
    </strong>
  </div>

  <button
    type="button"
    className="w-full mt-1 px-3 py-1 bg-indigo-600 hover:bg-indigo-500 rounded text-white"
    onClick={() => {
      const exportData = (nodes ?? [])
        .filter((n: any) => (showCollapsed ? true : n?.collapse_state !== "collapsed"))
        .map((n: any) => ({
          id: n?.id,
          label: n?.label,
          tick: n?.tick,
          state: n?.collapse_state,
          entropy: n?.entropy,
          goalMatchScore: n?.goalMatchScore,
          rewriteSuccessProb: n?.rewriteSuccessProb,
        }));

      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `collapse_timeline_tick${tickFilter ?? "all"}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }}
  >
    ⬇️ Export Collapse Timeline
  </button>
</div>

{/* 👥 Presence cursors (overlay; keep it outside the panel but still inside the component’s Fragment) */}
<PresenceLayer others={others} />
</>
); // end return of QuantumFieldCanvas

// ───────────────────────────────────────────────────────────────
// Loader
// ───────────────────────────────────────────────────────────────
export const QuantumFieldCanvasLoader: React.FC<{
  containerId: string;
  tickFilter?: number;
  showCollapsed?: boolean;
  onTeleport?: (id: string) => void;
}> = ({ containerId, tickFilter, showCollapsed, onTeleport }) => {
  const [data, setData] = useState<{ nodes: any[]; links: any[] }>({
    nodes: [],
    links: [],
  });

  // Try rich QFC view first (with layout + traces), then fall back to basic graph
  useEffect(() => {
    let cancelled = false;

    async function load() {
      // 1) Preferred: /api/qfc_view/{containerId}
      try {
        const res = await fetch(`/api/qfc_view/${encodeURIComponent(containerId)}`);
        if (!res.ok) throw new Error(String(res.statusText));
        const json: any = await res.json();

        const rawNodes: any[] = json.nodes || [];
        const links: any[] = json.links || [];

        // Optional layout snap
        const snappedNodes = snapToEntangledMemoryLayout(rawNodes, containerId);

        // Annotate like your original logic
        const annotatedNodes = snappedNodes.map((node: any) => {
          const glyphTrace = node.glyphTrace ?? node.memory ?? null;

          let goalType: "goal" | "strategy" | "milestone" | null = null;
          const label = (node.label || "").toLowerCase();
          if (label.includes("goal")) goalType = "goal";
          else if (label.includes("strategy")) goalType = "strategy";
          else if (label.includes("milestone")) goalType = "milestone";

          let memoryTrace = null;
          if (Array.isArray(glyphTrace) && glyphTrace.length > 0) {
            const last = glyphTrace[glyphTrace.length - 1] || {};
            memoryTrace = {
              summary: last.summary || last.intent || "Observed symbolic memory",
              containerId: node.containerId || containerId,
              agentId: node.agentId || "aion-agent",
            };
          }

          return {
            ...node,
            goalType,
            memoryTrace,
            containerId: node.containerId || containerId || "kevin_1244.dc.json",
          };
        });

        if (!cancelled) {
          setData({ nodes: annotatedNodes, links });
        }
        return; // success path done
      } catch {
        // continue to fallback
      }

      // 2) Fallback: /api/qfc/graph?container_id=...
      try {
        const r = await fetch(`/api/qfc/graph?container_id=${encodeURIComponent(containerId)}`);
        const j = r.ok ? await r.json() : { nodes: [], links: [] };
        if (!cancelled) {
          setData({
            nodes: j.nodes || [],
            links: j.links || [],
          });
        }
      } catch {
        if (!cancelled) {
          setData({ nodes: [], links: [] }); // non-fatal
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [containerId]);

  // Inject scrolls into active field via backend + request focus on injected glyph
  useEffect(() => {
    const handleScrollInjection = async (event: any) => {
      const { glyphId, scrollContent } = event?.detail || {};
      if (!glyphId) return;

      try {
        const response = await fetch("/api/inject_scroll", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ glyph: glyphId, scroll: scrollContent }),
        });

        const result = await response.json();

        if (result && Array.isArray(result.glyphs)) {
          setData((prev) => {
            const existingIds = new Set(prev.nodes.map((n) => n.id));
            const mergedNodes = [
              ...prev.nodes,
              ...result.glyphs.filter((g: any) => !existingIds.has(g.id)),
            ];
            return { ...prev, nodes: mergedNodes };
          });

          // ask the canvas to focus (decoupled)
          window.dispatchEvent(new CustomEvent("focus_glyph", { detail: { glyphId } }));
        }
      } catch (err) {
        console.error("Scroll injection failed:", err);
      }
    };

    window.addEventListener("scroll_injected", handleScrollInjection);
    return () => window.removeEventListener("scroll_injected", handleScrollInjection);
  }, []);

  // Live updates from socket
  useQfcSocket(containerId, (payload) => {
    if (!payload) return;
    setData((prev) => {
      const nextNodes = payload.nodes || [];
      const nextLinks = payload.links || [];
      const byId = new Map<string, any>();
      for (const n of prev.nodes) byId.set(n.id, n);
      for (const n of nextNodes) if (n?.id) byId.set(n.id, n);
      return {
        nodes: Array.from(byId.values()),
        links: [...prev.links, ...nextLinks],
      };
    });
  });

  // Default onTeleport (navigate to /dimension/*)
  const handleTeleport = (id: string) => {
    if (onTeleport) return onTeleport(id);
    const node = data.nodes.find((n) => n.id === id);
    const targetContainer = node?.containerId;
    if (targetContainer) {
      window.location.href = `/dimension/${targetContainer.replace(".dc.json", "")}`;
    } else {
      alert("No container ID found for node: " + id);
    }
  };

  return (
    <QuantumFieldCanvas
      nodes={data.nodes as GlyphNode[]}
      links={data.links as any[]}
      tickFilter={tickFilter}
      showCollapsed={showCollapsed}
      onTeleport={handleTeleport}
    />
  );
};

// Utility: is a node within observer's field of view
function isInObserverView(
  nodePosition: [number, number, number],
  observerPosition: [number, number, number],
  direction: [number, number, number],
  fovAngle: number = Math.PI / 3
) {
  const vecToNode = new THREE.Vector3(
    nodePosition[0] - observerPosition[0],
    nodePosition[1] - observerPosition[1],
    nodePosition[2] - observerPosition[2]
  ).normalize();
  const observerDir = new THREE.Vector3(...direction).normalize();
  const angle = observerDir.angleTo(vecToNode);
  return angle <= fovAngle / 2;
}