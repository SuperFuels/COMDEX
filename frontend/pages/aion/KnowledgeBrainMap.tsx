/**
📄 KnowledgeBrainMap.tsx

🧠 Knowledge Brain Map Visualization for AION & IGI  
Renders a living 3D knowledge graph with glowing entangled glyph zones.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌌 Knowledge Brain Map – Design Rubric
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Live WebSocket Updates from KG & Collapse Feedback
✅ Confidence-Driven Node Glow Intensity (CodexMetrics)
✅ ⚛ QGlyph Collapse Ripple Visualization
✅ ↔ Entangled Node Link Highlighting (Real-Time)
✅ Success vs Failure Gradient Color Mapping
✅ Animated Ripple Glow Effects for Collapse Events
✅ GHX Holographic Glyph Overlays (Floating Symbols)
✅ Replay Glyph Snapshot Metadata (H7)
✅ Scalable for Cross-Agent KG Fusion & Collective IQ
✅ Ready for Recursive Self-Optimization Loops
*/

import React, { useState, useRef } from "react";
import dynamic from "next/dynamic";
import * as THREE from "three";
import useWebSocket from "../../hooks/useWebSocket";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), { ssr: false });

interface NodeData {
  id: string;
  label: string;
  confidence: number;
  entropy: number;
  status: "success" | "failure" | "collapse" | "neutral";
  ripple?: boolean;
  snapshot_id?: string; // ✅ NEW: container snapshot for replay context
}

interface LinkData {
  source: string;
  target: string;
}

const KnowledgeBrainMap: React.FC = () => {
  const [graphData, setGraphData] = useState<{ nodes: NodeData[]; links: LinkData[] }>({
    nodes: [],
    links: [],
  });

  const fgRef = useRef<any>();

  // ✅ WebSocket listener for KG + Fusion + Replay Events
  useWebSocket("/ws/brain-map", (data) => {
    if (data.type === "node_update") updateNode(data.node);
    else if (data.type === "link_update") updateLink(data.link);
    else if (data.type === "collapse_ripple") triggerRippleAnimation(data.entangled_nodes);
    else if (data.type === "fusion_confidence_update") handleFusionConfidenceUpdate(data);
    else if (data.type === "fusion_gradient_update") handleFusionGradientUpdate(data);
    else if (data.type === "fusion_consensus") handleFusionConsensus(data);
    else if (data.type === "glyph_replay") handleGlyphReplayEvent(data); // ✅ NEW
    else if (data.type === "kg_snapshot") setGraphData({ nodes: data.nodes, links: data.links });
  });

  // 🔧 Node updater
  const updateNode = (node: any) => {
    setGraphData((prev) => {
      const updated = [...prev.nodes];
      const idx = updated.findIndex((n) => n.id === node.id);
      if (idx >= 0) updated[idx] = { ...updated[idx], ...node };
      else updated.push({ ...node, ripple: false });
      return { ...prev, nodes: updated };
    });
  };

  // 🔧 Link updater
  const updateLink = (link: any) => {
    setGraphData((prev) => {
      const exists = prev.links.some((l) => l.source === link.source && l.target === link.target);
      return exists ? prev : { ...prev, links: [...prev.links, link] };
    });
  };

  // 🔥 Ripple animation for collapse events
  const triggerRippleAnimation = (entangledNodes: string[]) => {
    setGraphData((prev) => ({
      ...prev,
      nodes: prev.nodes.map((node) =>
        entangledNodes.includes(node.id) ? { ...node, ripple: true } : node
      ),
    }));
    setTimeout(() => {
      setGraphData((prev) => ({
        ...prev,
        nodes: prev.nodes.map((node) =>
          entangledNodes.includes(node.id) ? { ...node, ripple: false } : node
        ),
      }));
    }, 1500);
  };

  // 🌐 Fusion Event Handlers
  const handleFusionConfidenceUpdate = (data: any) => {
    setGraphData((prev) => ({
      ...prev,
      nodes: prev.nodes.map((node) =>
        data.entangled_nodes.includes(node.id)
          ? { ...node, confidence: Math.max(0, Math.min(1, node.confidence + data.confidence_delta)) }
          : node
      ),
    }));
  };

  const handleFusionGradientUpdate = (data: any) => {
    setGraphData((prev) => ({
      ...prev,
      nodes: prev.nodes.map((node) =>
        data.entangled_nodes.includes(node.id)
          ? { ...node, status: "neutral", ripple: true }
          : node
      ),
    }));
    setTimeout(() => {
      setGraphData((prev) => ({
        ...prev,
        nodes: prev.nodes.map((node) =>
          data.entangled_nodes.includes(node.id) ? { ...node, ripple: false } : node
        ),
      }));
    }, 1200);
  };

  const handleFusionConsensus = (data: any) => {
    setGraphData((prev) => ({
      ...prev,
      nodes: prev.nodes.map((node) =>
        node.id === data.glyph_id ? { ...node, confidence: data.confidence, status: "success" } : node
      ),
    }));
  };

  // 🎬 Handle Glyph Replay Events (H7)
  const handleGlyphReplayEvent = (data: any) => {
    const { glyphs, container_id, tick_start, tick_end, snapshot_id } = data;
    setGraphData((prev) => {
      const replayNodes = glyphs.map((g: any) => ({
        id: g.id || g.glyph,
        label: g.glyph,
        confidence: 0.8,
        entropy: 0.1,
        status: "neutral",
        ripple: true,
        snapshot_id, // ✅ attach snapshot for replay
      }));
      const replayLinks = (data.links || []).map((l: any) => ({ source: l.source, target: l.target }));
      return { nodes: [...prev.nodes, ...replayNodes], links: [...prev.links, ...replayLinks] };
    });
  };

  // 🎨 Glow color
  const getNodeColor = (node: NodeData) => {
    if (node.ripple) return "cyan";
    if (node.status === "failure") return "red";
    if (node.status === "success") return "limegreen";
    if (node.status === "collapse") return "deepskyblue";
    return "white";
  };

  // 🔆 Glow intensity scaling
  const getGlowIntensity = (node: NodeData) => {
    const base = Math.max(0.2, Math.min(2.5, node.confidence * 1.5 + node.entropy * 0.05));
    return node.ripple ? base * 2.2 : base;
  };

  return (
    <div style={{ width: "100%", height: "100vh", background: "black" }}>
      <ForceGraph3D
        ref={fgRef}
        graphData={graphData}
        nodeAutoColorBy="status"
        nodeThreeObject={(node: any) => {
          const n = node as NodeData;
          const group = new THREE.Group();

          // Core glow
          const glow = new THREE.Mesh(
            new THREE.SphereGeometry(6),
            new THREE.MeshBasicMaterial({ color: getNodeColor(n), transparent: true, opacity: 0.85 })
          );
          const halo = new THREE.Mesh(
            new THREE.SphereGeometry(10),
            new THREE.MeshBasicMaterial({ color: getNodeColor(n), transparent: true, opacity: 0.25 })
          );
          glow.scale.setScalar(getGlowIntensity(n));
          halo.scale.setScalar(getGlowIntensity(n) * 1.5);
          group.add(glow);
          group.add(halo);

          // ✨ GHX holographic floating label with snapshot ID
          const spriteCanvas = document.createElement("canvas");
          const ctx = spriteCanvas.getContext("2d")!;
          spriteCanvas.width = 256;
          spriteCanvas.height = 80;
          ctx.font = "28px Orbitron";
          ctx.fillStyle = "cyan";
          ctx.textAlign = "center";
          ctx.fillText(n.label || "⧖", 128, 35);
          if (n.snapshot_id) {
            ctx.font = "16px Orbitron";
            ctx.fillStyle = "white";
            ctx.fillText(`Snapshot: ${n.snapshot_id}`, 128, 65);
          }

          const texture = new THREE.CanvasTexture(spriteCanvas);
          const spriteMaterial = new THREE.SpriteMaterial({ map: texture, transparent: true });
          const sprite = new THREE.Sprite(spriteMaterial);
          sprite.scale.set(45, 15, 1);
          sprite.position.set(0, 15, 0);
          group.add(sprite);

          return group;
        }}
        linkColor={() => "rgba(0,255,255,0.3)"}
        linkWidth={1.5}
        backgroundColor="black"
        onNodeClick={(node: any) =>
          alert(
            `Glyph: ${node.label}\nConfidence: ${node.confidence}\nEntropy: ${node.entropy}\n${
              node.snapshot_id ? `Snapshot: ${node.snapshot_id}` : ""
            }`
          )
        }
      />
    </div>
  );
};

export default KnowledgeBrainMap;