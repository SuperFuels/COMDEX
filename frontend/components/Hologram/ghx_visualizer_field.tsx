// File: frontend/components/Hologram/ghx_visualizer_field.tsx
'use client';

import React, { useEffect, useRef, useState } from "react";
import useWebSocket from "@/hooks/useWebSocket";
import {
  renderGHXBeam,
  renderGlyphCollapse,
  renderPatternOverlay,
} from "./ghxFieldRenderers";

interface GHXVisualizerProps {
  containerId: string;
  width?: number;
  height?: number;
  className?: string;
  /** Optional overlay content (e.g., <CodexHUD />) rendered on top */
  children?: React.ReactNode;
}

export default function GHXVisualizerField({
  containerId,
  width = 1200,
  height = 800,
  className,
  children,
}: GHXVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [ctx, setCtx] = useState<CanvasRenderingContext2D | null>(null);
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null);

  // keep a live ref so WS handler doesn't close over stale ctx
  useEffect(() => {
    ctxRef.current = ctx;
  }, [ctx]);

  // Initialize canvas (handle devicePixelRatio) and clear on container change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const context = canvas.getContext("2d");
    if (!context) return;

    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, width, height);
    setCtx(context);

    // clear when containerId changes
    return () => {
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      context.clearRect(0, 0, width, height);
    };
  }, [width, height, containerId]);

  // WebSocket message handler
  const handleWebSocketMessage = (data: any) => {
    const type = data?.type || data?.event;
    const context = ctxRef.current;
    if (!type || !context) return;

    switch (type) {
      case "ghx_beam":
        renderGHXBeam(context, data.payload);
        break;
      case "ghx_collapse":
        renderGlyphCollapse(context, data.payload);
        break;
      case "ghx_pattern":
        renderPatternOverlay(context, data.payload);
        break;
      case "container_loaded":
        if (data.container_id === containerId) {
          context.clearRect(0, 0, width, height);
        }
        break;
      default:
        // ignore unknown events
        break;
    }
  };

  // Open WS for GHX events
  useWebSocket("/ws/ghx", handleWebSocketMessage, [
    "ghx_beam",
    "ghx_collapse",
    "ghx_pattern",
    "container_loaded",
  ]);

  return (
    <div className={`relative w-full h-full ${className ?? ""}`}>
      <canvas
        ref={canvasRef}
        className="rounded-2xl shadow-xl border border-gray-800 bg-black block"
        // CSS size; actual pixel size handled in effect for DPR
        style={{ width, height }}
      />
      {children ? (
        <div className="absolute inset-0 pointer-events-none">
          {children}
        </div>
      ) : null}
    </div>
  );
}