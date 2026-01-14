// File: frontend/components/Hologram/quantum_field_canvas.tsx

import React, { useRef, useEffect, useState, useMemo, useCallback } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useSharedField } from "../../collab/useSharedField";
import { PresenceLayer } from "../../collab/PresenceLayer";

import { QWaveBeam, BeamProps } from "@/components/QuantumField/beam_renderer";
import TraceCollapseRenderer from "@/components/QuantumField/Replay/trace_collapse_renderer";
import { snapToEntangledMemoryLayout } from "@/lib/layout";
import { useQfcSocket } from "@/hooks/useQfcSocket";
import HoverAgentLogicView from "@/components/QuantumField/Memory/hover_agent_logic_view";
import { QWavePreviewPanel } from "@/components/QuantumField/QWavePreviewPanel";
import FrameBridge from "../../plugins/FrameBridge";
import PluginHUD from "../../plugins/PluginHUD";
import QuantumFieldCanvasView from "./QuantumFieldCanvasView";
import { useNormalizedQfcGraph } from "./useNormalizedQfcGraph";
import renderQWaveBeams from "./renderQWaveBeams";
import { QuantumFieldCanvasLoader } from "./QuantumFieldCanvasLoader";

// NEW
import type { HoloIR } from "@/lib/types/holo";
import {
  runHoloSnapshot,
  type HoloRunResult,
} from "../../../Glyph_Net_Browser/src/lib/api/holo";

// 🔧 shape / feature imports
import EntropyNode from "@/components/QuantumField/styling/EntropyNode";
import { HighlightedOperator } from "@/components/QuantumField/highlighted_symbolic_operators";
import ReplayTrails from "./ReplayTrails";
import { Node } from "@/components/QuantumField/Node";
import { LinkLine } from "@/components/QuantumField/LinkLine";
import ReplayPulse from "@/components/QuantumField/Replay/ReplayPulse";
import {
  useLoadQWaveBeamsLocal,
  getStaticTrailsLocal,
  mergePredictedGraphLocal,
} from "./qfcLocal";

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

import {
  broadcast_qfc_update,
  getLinkColor,
  setOrbitTargetToGlyphFactory,
  centerToGlyphFactory,
} from "./qfcHelpers";

// ------------------ Types ------------------

interface Link {
  source: string;
  target: string;
  type?: "entangled" | "teleport" | "logic";
  tick?: number;
}

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
  nodes: ExtendedGlyphNode[];
  links: Link[];

  beams?: any[];

  tickFilter?: number;
  showCollapsed?: boolean;
  onTeleport?: (targetContainerId: string) => void;

  containerId?: string;

  predictedMode?: boolean;
  predictedOverlay?: {
    nodes: ExtendedGlyphNode[];
    links: Link[];
  };

  // NEW: active hologram bound to this QFC view (optional)
  holo?: HoloIR | null;
}

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

  // NEW: holo run state
  const [isRunningHolo, setIsRunningHolo] = useState(false);
  const [lastRunResult, setLastRunResult] = useState<HoloRunResult | null>(null);

  // Camera & controls
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<any>(null);

  // QFC focus (guarded)
  const qfcFocus = (typeof useQFCFocus === "function" ? useQFCFocus() : null) as any;
  const setFocus: (id: string) => void =
    qfcFocus && typeof qfcFocus.setFocus === "function" ? qfcFocus.setFocus : () => {};

  // Branch / observer state
  const [selectedBranch, setSelectedBranch] = useState("trail-1");
  const availableBranches = ["trail-1", "trail-2", "trail-3"];

  const [observerPosition, setObserverPosition] =
    useState<[number, number, number]>([0, 0, 0]);
  const observerDirection: [number, number, number] = [0, 0, -1];

  // Beams + replay
  const [beamData, setBeamData] = useState<any[] | null>([]);
  const [replayFrames, setReplayFrames] = useState<any[]>([]);
  const [isReplaying, setIsReplaying] = useState(false);
  const [playbackIndex, setPlaybackIndex] = useState(0);

  // 1) Load beams (local hook may give anything, so we normalize later)
  useLoadQWaveBeamsLocal(setBeamData);

  // 2) Trails (static)
  const { collapseTrails, breakthroughTrails, deadendTrails } = useMemo(
    getStaticTrailsLocal,
    []
  );

  const { tickFilter, showCollapsed = false, containerId } = props;

  // 🔐 SAFETY: normalize props before handing to useNormalizedQfcGraph
  const safePropsNodes: ExtendedGlyphNode[] = useMemo(
    () => (Array.isArray(props.nodes) ? props.nodes : []),
    [props.nodes]
  );

  const safePropsLinks: Link[] = useMemo(
    () => (Array.isArray(props.links) ? props.links : []),
    [props.links]
  );

  const roomId = containerId ?? "default";

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
    propsNodes: safePropsNodes,
    propsLinks: safePropsLinks,
    sharedNodes,
    sharedLinks,
    sharedBeams,
    tickFilter,
    showCollapsed,
  });

  // Orbit helpers
  const setOrbitTargetToGlyph = useMemo(
    () => setOrbitTargetToGlyphFactory({ nodes, cameraRef, controlsRef }),
    [nodes]
  );

  const centerToGlyph = useMemo(
    () =>
      centerToGlyphFactory({
        mergedNodes,
        setObserverPosition,
        setOrbitTargetToGlyph,
      }),
    [mergedNodes, setObserverPosition, setOrbitTargetToGlyph]
  );

  // Focus events → center camera
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

  // 6) QWave beams JSX (normalize beamData here too)
  const qwaveBeams = useMemo(
    () =>
      renderQWaveBeams({
        beamData: Array.isArray(beamData) ? beamData : [],
        setSelectedBeam,
      }),
    [beamData, setSelectedBeam]
  );

  const specialOps = useMemo(() => new Set(["⧖", "↔", "⬁", "🧬", "🪞"]), []);
  const [focusedNode, setFocusedNode] = useState<string | null>(null);

  // Live graph = props + adds
  const liveNodes = useMemo<ExtendedGlyphNode[]>(
    () => [...(safePropsNodes || []), ...(graphAdds.nodes as ExtendedGlyphNode[])],
    [safePropsNodes, graphAdds.nodes]
  );
  const liveLinks = useMemo<Link[]>(
    () => [...(safePropsLinks || []), ...(graphAdds.links as Link[])],
    [safePropsLinks, graphAdds.links]
  );

  // Presence: viewport from orbit
  const lastViewportSent = useRef<number>(0);

  const handleOrbitChange = useCallback(() => {
    if (!controlsRef.current || !cameraRef.current || !applyOp?.setViewport) return;

    const now = Date.now();
    if (now - lastViewportSent.current < 150) return;
    lastViewportSent.current = now;

    const t = controlsRef.current.target as THREE.Vector3;
    const cam = cameraRef.current!;
    const zoom = cam.position.distanceTo(new THREE.Vector3(t.x, t.y, t.z));

    applyOp.setViewport([t.x, t.y, t.z], zoom);
  }, [applyOp]);

  // Presence: cursors
  useEffect(() => {
    if (!applyOp?.setCursor) return;
    const onMove = (e: MouseEvent) => applyOp.setCursor(e.clientX, e.clientY);
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, [applyOp]);

  // Presence: selection
  const selectGlyph = useCallback(
    (ids: Array<string | number>) => {
      if (!applyOp?.setSelection) return;
      applyOp.setSelection(ids.map(String));
    },
    [applyOp]
  );

  // Decide container id for QFC socket
  const socketContainerId = useMemo(() => {
    const fromNodes = (safePropsNodes || []).find((n: any) => !!n.containerId)?.containerId;
    return (fromNodes || (props as any).containerId || "ucs_hub") as string;
  }, [safePropsNodes, (props as any).containerId]);

  // WebSocket subscription for QFC updates
  useQfcSocket(socketContainerId, (payload: { nodes?: any[]; links?: any[] }) => {
    setGraphAdds((prev) => ({
      nodes: [...prev.nodes, ...(payload?.nodes ?? [])],
      links: [...prev.links, ...(payload?.links ?? [])],
    }));
  });

  // Demo: fetch test beams
  useEffect(() => {
    fetch("/api/test-mixed-beams")
      .then((res) => res.json())
      .then((data) => {
        setBeamData(Array.isArray(data?.beams) ? data.beams : []);
      })
      .catch(() => void 0);
  }, []);

  // Replay playback loop
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
    }, 100);
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

      if (result && result.glyphs) {
        broadcast_qfc_update(result);
        setOrbitTargetToGlyph(glyph);

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

  // 🔁 Run current .holo through backend execution pipeline
  const handleRunHolo = useCallback(async () => {
    if (!props.holo) {
      console.warn("[QFC] No active Holo bound to QuantumFieldCanvas; skipping run.");
      return;
    }

    setIsRunningHolo(true);
    try {
      const result = await runHoloSnapshot({
        holo: props.holo,
        inputCtx: {
          source: "qfc_ui",
          container_id: props.containerId ?? "ucs_hub",
        },
        mode: "qqc",
      });

      setLastRunResult(result || null);

      // TODO: when backend returns updated_holo / beams / frames,
      // you can project them into QFC state here.
      // if (result.updated_holo) { ... }
      // if (Array.isArray(result.metrics?.frames)) { ... }
    } catch (err: any) {
      console.error("[QFC] Run .holo failed:", err);
      setLastRunResult({
        status: "error",
        mode: "qqc",
        holo_id: props.holo?.holo_id,
        container_id: props.holo?.container_id,
        output: null,
        updated_holo: null,
        metrics: { error: err?.message ?? String(err) },
      });
    } finally {
      setIsRunningHolo(false);
    }
  }, [props.holo, props.containerId]);

  // Window shims for glyphwave / qfc_update events
  useEffect(() => {
    const onForkBeam = (e: any) => {
      const p = e?.detail ?? {};
      const id = p.wave_id ?? crypto.randomUUID();
      setBeams((prev) =>
        prev.some((b: any) => b?.id === id) ? prev : [{ id, ...p }, ...prev].slice(0, 200)
      );
    };

    const onIndex = (_e: any) => {
      // index_update hook, keep if you want metrics
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

  // Extra listener (if anything else re-broadcasts qfc_update)
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

  /* ── Render ── */
  return (
    <QuantumFieldCanvasView
      beams={beams}
      liveNodes={liveNodes}
      liveLinks={liveLinks}
      mergedNodes={mergedNodes as any}
      mergedLinks={mergedLinks as any}
      beamData={Array.isArray(beamData) ? beamData : []}
      qwaveBeams={qwaveBeams}
      onTeleport={props.onTeleport}
      cameraRef={cameraRef}
      controlsRef={controlsRef}
      observerPosition={observerPosition}
      observerDirection={observerDirection}
      showPredictedLayer={showPredictedLayer}
      splitScreen={splitScreen}
      predictedMode={predictedMode}
      predictedOverlayData={props.predictedOverlay ?? null}
      predictedOverlay={predictedOverlay}
      onTogglePredictedLayer={() => setShowPredictedLayer((v) => !v)}
      onToggleSplitScreen={() => setSplitScreen((v) => !v)}
      onTogglePredictedMode={() => setPredictedMode((v) => !v)}
      onTogglePredictedOverlay={() => setPredictedOverlay((v) => !v)}
      isReplaying={isReplaying}
      replayFrames={replayFrames}
      playbackIndex={playbackIndex}
      setIsReplaying={setIsReplaying}
      setPlaybackIndex={setPlaybackIndex}
      availableBranches={availableBranches}
      selectedBranch={selectedBranch}
      setSelectedBranch={setSelectedBranch}
      onRetryFromBranch={handleRetryFromBranch}
      setSelectedBeam={setSelectedBeam}
      collapseTrails={collapseTrails}
      breakthroughTrails={breakthroughTrails}
      deadendTrails={deadendTrails}
      getLinkColor={getLinkColor}
      handleOrbitChange={handleOrbitChange}
      tickFilter={tickFilter}
      showCollapsed={showCollapsed}
      others={others}
      onDroppedScroll={handleDroppedScroll}
      // NEW: holo-run wiring
      canRunHolo={!!props.holo}
      isRunningHolo={isRunningHolo}
      onRunHolo={handleRunHolo}
      lastRunStatus={lastRunResult?.status}
    />
  );
}