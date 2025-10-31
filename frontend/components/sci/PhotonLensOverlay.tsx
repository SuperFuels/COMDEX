// =====================================================
//  🌌 PhotonLens Overlay — Quantum Resonance Visualizer v3.2
//  Now includes Audio Resonance Feedback Layer
// =====================================================
"use client";

import React, { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

// ─────────────────────────────────────────────
// 💠 Type Definitions
// ─────────────────────────────────────────────
type PhotonFrame = { waves?: any[] };

interface GlowPulse {
  hue: number;
  intensity: number;
  radius: number;
  ts: number;
  dur: number;
}

interface BridgeOp {
  op?: string;
  color?: string;
  alpha?: number;
  decay?: boolean;
}
// ─────────────────────────────────────────────
// 🌊 Component
// ─────────────────────────────────────────────
export default function PhotonLensOverlay({
  wsUrl = process.env.NEXT_PUBLIC_QFC_WS || "ws://localhost:8003/ws/qfc",
  containerId = "sci:editor:init",
}: {
  wsUrl?: string;
  containerId?: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [status, setStatus] = useState("🔭 Initializing PhotonLens…");
  const [connected, setConnected] = useState(false);
  const [frames, setFrames] = useState<PhotonFrame[]>([]);
  const [bridgeOps, setBridgeOps] = useState<BridgeOp[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const animationRef = useRef<number>();
  const glowDecay = useRef<number>(0.96);
  const audioCtxRef = useRef<AudioContext | null>(null);
  // 🔥 SQI resonance pulses from cognition core
  const [mutationPulses, setMutationPulses] = useState<any[]>([]);
  // ─────────────────────────────────────────────
  // 🧠 Audio System Setup (Web Audio API)
  // ─────────────────────────────────────────────
  useEffect(() => {
    if (!audioCtxRef.current) {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioCtxRef.current = ctx;
    }
  }, []);

  const playTone = (frequency: number, duration = 0.25, type: OscillatorType = "sine") => {
    const ctx = audioCtxRef.current;
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.value = frequency;
    osc.type = type;
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  };

  const playOperatorTone = (op: string) => {
    switch (op) {
      case "⊕": playTone(432, 0.3, "sine"); break;         // Superposition
      case "↔": playTone(528, 0.4, "triangle"); break;     // Entanglement
      case "⟲": playTone(639, 0.5, "sawtooth"); break;     // Resonance
      case "∇": playTone(396, 0.2, "square"); break;       // Collapse
      case "μ": playTone(741, 0.35, "sine"); break;        // Measurement
      default: playTone(220, 0.15, "sine");
    }
  };

  // Helper for safe ctx access
  const getCtx = (): CanvasRenderingContext2D | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    return canvas.getContext("2d");
  };

  // ─────────────────────────────────────────────
  // 🌐 Connect to QFC WebSocket
  // ─────────────────────────────────────────────
  useEffect(() => {
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setStatus("🟢 Connected to QFC Field Stream");
      ws.send(JSON.stringify({ type: "subscribe", container_id: containerId }));
    };

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "qfc.frame") {
        setFrames((f) => [...f.slice(-80), msg.frame]);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setStatus("🔴 Disconnected — retrying…");
      setTimeout(() => window.location.reload(), 2500);
    };

    return () => ws.close();
  }, [wsUrl, containerId]);

  // ─────────────────────────────────────────────
  // ⚛ Listen for Photon–Symatics Bridge execution
  // ─────────────────────────────────────────────

  useEffect(() => {
    function handlePhotonRun(ev: CustomEvent) {
      const { results } = (ev.detail || {}) as { results?: BridgeOp[] };
      if (!results?.length) return;
      setBridgeOps(results);
      pulseOperators(results);
      results.forEach((r: BridgeOp) => {
        if (r.op) playOperatorTone(r.op);
      });
    }

    window.addEventListener("photon:run", handlePhotonRun as EventListener);
    return () => {
      window.removeEventListener("photon:run", handlePhotonRun as EventListener);
    };
  }, []);

    // ─────────────────────────────────────────────
    // 🖼️ Auto-resize canvas to container
    // ─────────────────────────────────────────────
    useEffect(() => {
      const resizeCanvas = () => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const parent = canvas.parentElement;
        if (parent) {
          canvas.width = parent.clientWidth;
          canvas.height = parent.clientHeight;
        }
      };
      resizeCanvas();
      window.addEventListener("resize", resizeCanvas);
      return () => window.removeEventListener("resize", resizeCanvas);
    }, []);

  // ─────────────────────────────────────────────
  // 🎨 Unified Render Loop
  // ─────────────────────────────────────────────
  useEffect(() => {
    const ctx = getCtx();
    if (!ctx) return;
    const canvas = ctx.canvas;
    let last = performance.now();

    const render = (now: number): void => {
      const dt = now - last;
      last = now;

      const w = canvas.width;
      const h = canvas.height;

      // Fade previous frame
      ctx.fillStyle = "rgba(0,0,0,0.25)";
      ctx.fillRect(0, 0, w, h);

      // Field waves
      const frame = frames.at(-1);
      if (frame?.waves) {
        frame.waves.forEach((_, i: number) => {
          const x = (i * 45 + now / 25) % w;
          const amp = (Math.sin(now / 600 + i) + 1) * 28;
          ctx.beginPath();
          ctx.strokeStyle = "rgba(60,180,255,0.35)";
          ctx.moveTo(x, h / 2 - amp);
          ctx.lineTo(x, h / 2 + amp);
          ctx.stroke();
        });
      }

      // Bridge operator pulses
      bridgeOps.forEach((op, idx) => {
        const { color, decay } = colorMap(op.op || "");
        const x = (w / (bridgeOps.length + 1)) * (idx + 1);
        const y = h / 2 + Math.sin(now / 300 + idx) * 60;
        const r = 30 + Math.sin(now / 200 + idx) * 10;

        ctx.beginPath();
        const grad = ctx.createRadialGradient(x, y, 0, x, y, r * 2);
        grad.addColorStop(0, `${color}AA`);
        grad.addColorStop(1, "transparent");
        ctx.fillStyle = grad;
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();

        ctx.font = "18px JetBrains Mono, monospace";
        ctx.fillStyle = color;
        ctx.fillText(op.op || "•", x - 6, y + 6);

        if (decay) op.alpha = (op.alpha || 1) * glowDecay.current;
      });

      // 🌌 SQI bloom pulses from cognition core
      mutationPulses.forEach(p => {
        const t = (performance.now() - p.ts) / p.dur;
        if (t > 1) return;

        const fade = 1 - t;
        const radius = p.radius * (1 + t * 2);
        const alpha = p.intensity * fade;

        const x = w * 0.5;
        const y = h * 0.5;

        const grad = ctx.createRadialGradient(x, y, 0, x, y, radius);
        grad.addColorStop(0, `hsla(${p.hue}, 90%, 60%, ${alpha})`);
        grad.addColorStop(1, `hsla(${p.hue}, 90%, 60%, 0)`);

        ctx.beginPath();
        ctx.fillStyle = grad;
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
      });

      // ✅ keep this last
      animationRef.current = requestAnimationFrame(render);
    };

    animationRef.current = requestAnimationFrame(render);
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [frames, bridgeOps, mutationPulses]);

  // 🎯 Listen for resonance mutation events
  useEffect(() => {
    function handleMutation(ev: any) {
      const d = ev.detail;
      if (!d?.pattern_id) return;

      const delta = Math.abs(d.delta ?? 0);
      if (delta < 0.005) return; // ignore tiny flickers

      const hue = (
        d.pattern_id
          .split("")
          .reduce((a: number, c: string) => a + c.charCodeAt(0), 0) % 360
      );
      const intensity = Math.min(delta * 4.5, 1.0);

      const pulse = {
        id: d.pattern_id + ":" + Date.now(),
        hue,
        intensity,
        radius: Math.max(0.1, intensity * 120),
        ts: performance.now(),
        dur: 600
      };

      setMutationPulses(p => [...p, pulse]);

      setTimeout(() =>
        setMutationPulses(p => p.filter(x => x.id !== pulse.id)),
        pulse.dur
      );
    }

    window.addEventListener("pattern_mutation", handleMutation);
    return () => window.removeEventListener("pattern_mutation", handleMutation);
  }, []);

  // ─────────────────────────────────────────────
  // 🌈 Operator pulse animation trigger
  // ─────────────────────────────────────────────
  function pulseOperators(results: BridgeOp[]): void {
    const ctx = getCtx();
    if (!ctx) return;
    const canvas = ctx.canvas;
    const w = canvas.width;
    const h = canvas.height;

    results.forEach((op, i) => {
      const { color } = colorMap(op.op || "");
      const x = (w / (results.length + 1)) * (i + 1);
      const y = h / 2;
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.arc(x, y, 35, 0, Math.PI * 2);
      ctx.stroke();
    });
  }

  // ─────────────────────────────────────────────
  // 🎨 Color map helper
  // ─────────────────────────────────────────────
  function colorMap(op: string): { color: string; decay: boolean } {
    switch (op) {
      case "⊕": return { color: "#00FFFF", decay: true };
      case "↔": return { color: "#FF00FF", decay: true };
      case "⟲": return { color: "#FFD700", decay: true };
      case "∇": return { color: "#FF5555", decay: true };
      case "μ": return { color: "#FFFFFF", decay: true };
      default:  return { color: "#8888FF", decay: false };
    }
  }

  // ─────────────────────────────────────────────
  // 🧠 Commit frame to Knowledge Graph
  // ─────────────────────────────────────────────
  async function commitFrameToKnowledge(): Promise<void> {
    const frame = frames.at(-1);
    if (!frame) {
      alert("No frame to commit.");
      return;
    }
    await fetch("/api/sci/commit_atom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        container_id: containerId,
        label: "PhotonLens Snapshot",
        frame,
      }),
    });
    setStatus("🧠 Frame committed to Knowledge Graph.");
  }

  // ─────────────────────────────────────────────
  // 🧩 Render Layout
  // ─────────────────────────────────────────────
  return (
    <div className="flex flex-col bg-neutral-950 border-l border-neutral-800 w-[38%] relative">
      {/* Status bar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-neutral-800 bg-neutral-900 text-xs">
        <span>{status}</span>
        <button
          onClick={commitFrameToKnowledge}
          disabled={!connected}
          className="px-2 py-1 bg-blue-700 hover:bg-blue-600 rounded border border-blue-500"
        >
          ⟲ Commit Frame
        </button>
      </div>

      {/* Canvas Field */}
      <canvas ref={canvasRef} className="flex-1 w-full h-full" />

      {/* Operator Legend Overlay */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        className="absolute bottom-2 left-2 text-[11px] text-zinc-300 bg-black/50 px-3 py-2 rounded-lg border border-zinc-700"
      >
        <span className="mr-3 text-cyan-400">⊕ Superposition</span>
        <span className="mr-3 text-pink-400">↔ Entanglement</span>
        <span className="mr-3 text-yellow-400">⟲ Resonance</span>
        <span className="mr-3 text-red-400">∇ Collapse</span>
        <span className="text-white">μ Measurement</span>
      </motion.div>
    </div>
  );
}