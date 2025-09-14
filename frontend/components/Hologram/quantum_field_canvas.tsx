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
import FrameBridge from "../../plugins/FrameBridge";
import PluginHUD  from "../../plugins/PluginHUD";
import QuantumFieldCanvasView from "./QuantumFieldCanvasView";
import { useNormalizedQfcGraph } from "./useNormalizedQfcGraph";
import renderQWaveBeams from "./renderQWaveBeams";
import { QuantumFieldCanvasLoader } from "./QuantumFieldCanvasLoader";

// 🔧 Import shape fixes from your earlier errors
import EntropyNode from "@/components/QuantumField/styling/EntropyNode"; // default
import { HighlightedOperator } from "@/components/QuantumField/highlighted_symbolic_operators"; // named
import ReplayTrails from "./ReplayTrails";
import { Node } from "@/components/QuantumField/Node";
import { LinkLine } from "@/components/QuantumField/LinkLine";
import ReplayPulse from "@/components/QuantumField/Replay/ReplayPulse";
import { useLoadQWaveBeamsLocal, getStaticTrailsLocal, mergePredictedGraphLocal } from "./qfcLocal";

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
import {
  broadcast_qfc_update,
  getLinkColor,
  setOrbitTargetToGlyphFactory,
  centerToGlyphFactory,
} from "./qfcHelpers";
// ------------------ Main Component ------------------

export default function QuantumFieldCanvas(props: QuantumFieldCanvasProps) {
  const [showPredictedLayer, setShowPredictedLayer] = useState(false);
  const [predictedMode, setPredictedMode] = useState(!!props.predictedMode);
  const [predictedOverlay, setPredictedOverlay] = useState(!!props.predictedOverlay);
  const [splitScreen, setSplitScreen] = useState(false);

  const [selectedBeam, setSelectedBeam] = useState<any | null>(null);
  const [hoveredNode, setHoveredNode] = useState<any | null>(null);
  const [beams, setBeams] = useState<any[]>([]);
  const [graphAdds, setGraphAdds] = useState<{ nodes: any[]; links: any[] }>({
    nodes: [],
    links: [],
  });

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

  const [observerPosition, setObserverPosition] =
    useState<[number, number, number]>([0, 0, 0]);
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

  const {
    nodes,
    links,
    effectiveBeams,
    useFallback,
    mergedNodes,
    mergedLinks,
  } = useNormalizedQfcGraph({
    propsNodes: props.nodes,
    propsLinks: props.links,
    sharedNodes,
    sharedLinks,
    sharedBeams,
    tickFilter,
    showCollapsed,
  });

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
    () => renderQWaveBeams({ beamData: beamData ?? [], setSelectedBeam }),
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
    const cam = cameraRef.current!;
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

  // 5C) Helper to push current glyph selection into presence (call from your selection logic)
  const selectGlyph = useCallback(
    (ids: Array<string | number>) => {
      if (!applyOp?.setSelection) return;
      applyOp.setSelection(ids.map(String)); // normalize ids
    },
    [applyOp]
  );

  // Decide which container to subscribe to (derive from nodes, or fall back)
  const socketContainerId = useMemo(() => {
    const fromNodes = (props.nodes || []).find((n: any) => !!n.containerId)?.containerId;
    return (fromNodes || (props as any).containerId || "ucs_hub") as string;
  }, [props.nodes, (props as any).containerId]);

// Subscribe to QFC websocket updates (single top-level hook; no conditionals)
useQfcSocket(
  socketContainerId,
  (payload: { nodes?: any[]; links?: any[] }) => {
    setGraphAdds((prev) => ({
      nodes: [...prev.nodes, ...(payload?.nodes ?? [])],
      links: [...prev.links, ...(payload?.links ?? [])],
    }));
  }
);

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
    setBeams((prev) =>
      prev.some((b: any) => b?.id === id)
        ? prev
        : [{ id, ...p }, ...prev].slice(0, 200)
    );
  };

  const onIndex = (_e: any) => {
    // HUD/metrics updates welcome here if desired
  };

  const onQfc = (e: any) => {
    const p = e?.detail ?? {};
    setGraphAdds((prev) => ({
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

/* ── Render (inside QuantumFieldCanvas) ── */
return (
  <QuantumFieldCanvasView
    /* scene + live data */
    beams={beams}
    liveNodes={liveNodes}
    liveLinks={liveLinks}
    mergedNodes={mergedNodes as any}
    mergedLinks={mergedLinks as any}
    beamData={beamData}
    qwaveBeams={qwaveBeams}

    /* nav + refs */
    onTeleport={props.onTeleport}
    cameraRef={cameraRef}
    controlsRef={controlsRef}
    observerPosition={observerPosition}
    observerDirection={observerDirection}

    /* overlays/toggles */
    showPredictedLayer={showPredictedLayer}
    splitScreen={splitScreen}
    predictedMode={predictedMode}
    predictedOverlayData={props.predictedOverlay ?? null}
    predictedOverlay={predictedOverlay} 
    onTogglePredictedLayer={() => setShowPredictedLayer(v => !v)}
    onToggleSplitScreen={() => setSplitScreen(v => !v)}
    onTogglePredictedMode={() => setPredictedMode(v => !v)}
    onTogglePredictedOverlay={() => setPredictedOverlay(v => !v)}

    /* replay */
    isReplaying={isReplaying}
    replayFrames={replayFrames}
    playbackIndex={playbackIndex}
    setIsReplaying={setIsReplaying}
    setPlaybackIndex={setPlaybackIndex}

    /* branches */
    availableBranches={availableBranches}
    selectedBranch={selectedBranch}
    setSelectedBranch={setSelectedBranch}
    onRetryFromBranch={handleRetryFromBranch}

    /* beams selection */
    setSelectedBeam={setSelectedBeam}

    /* trails + helpers */
    collapseTrails={collapseTrails}
    breakthroughTrails={breakthroughTrails}
    deadendTrails={deadendTrails}
    getLinkColor={getLinkColor}

    /* orbit + presence */
    handleOrbitChange={handleOrbitChange}
    tickFilter={tickFilter}
    showCollapsed={showCollapsed}
    others={others}

    /* DnD handler */
    onDroppedScroll={handleDroppedScroll}
  />
);
} // ← closes QuantumFieldCanvas