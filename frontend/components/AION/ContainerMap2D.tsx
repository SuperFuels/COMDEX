'use client';

import React, { useEffect, useState, useRef, useCallback } from "react";
import useWebSocket from "@/hooks/useWebSocket";

type ContainerInfo = {
  id: string;
  name: string;
  in_memory: boolean;
  connected: string[];
  glyph?: string;
  region?: string;
};

type PositionMap = Record<string, { x: number; y: number }>;

export interface ContainerMap2DProps {
  mapData?: ContainerInfo[];
  activeId?: string;
  onContainerClick?: (id: string) => void;
}

export default function ContainerMap2D({
  mapData,
  activeId,
  onContainerClick,
}: ContainerMap2DProps) {
  const [containers, setContainers] = useState<ContainerInfo[]>([]);
  const [positions, setPositions] = useState<PositionMap>({});
  const [message, setMessage] = useState<string | null>(null);
  const [regions, setRegions] = useState<string[]>([]);
  const containerRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const { connected } = useWebSocket("/ws", (data: any) => {
    if (data.type === "glyph_update" || data.type === "container_update") {
      fetchContainers();
    }
  });

  const fetchContainers = () => {
    fetch("/api/aion/containers")
      .then((res) => res.json())
      .then((data) => {
        const list: ContainerInfo[] = data.containers || [];
        setContainers(list);
        const uniqueRegions = Array.from(new Set(list.map((c) => c.region ?? "Unassigned")));
        setRegions(uniqueRegions);
        setTimeout(updatePositions, 100);
      })
      .catch(() => {});
  };

  useEffect(() => {
    if (!mapData) fetchContainers();
    else setContainers(mapData);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapData]);

  useEffect(() => {
    const refresh = () => fetchContainers();
    window.addEventListener("glyph_update", refresh);
    return () => window.removeEventListener("glyph_update", refresh);
  }, []);

  useEffect(() => {
    const interval = setInterval(fetchContainers, 5000);
    return () => clearInterval(interval);
  }, []);

  const updatePositions = () => {
    const next: PositionMap = {};
    for (const id in containerRefs.current) {
      const el = containerRefs.current[id];
      if (el) {
        const rect = el.getBoundingClientRect();
        next[id] = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
      }
    }
    setPositions(next);
  };

  useEffect(() => {
    setTimeout(updatePositions, 100);
  }, [containers]);

  const setContainerRef = useCallback((id: string) => {
    return (el: HTMLDivElement | null) => {
      containerRefs.current[id] = el;
    };
  }, []);

  const handleTeleport = async (targetId: string) => {
    if (onContainerClick) return onContainerClick(targetId);

    try {
      const res = await fetch("/api/aion/teleport", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target: targetId }),
      });
      const result = await res.json();
      if (res.ok) {
        setMessage(`🌀 Teleported to ${targetId}`);
        containerRefs.current[targetId]?.scrollIntoView({ behavior: "smooth", block: "center" });
      } else {
        setMessage(`❌ Failed: ${result.detail || "Unknown error"}`);
      }
    } catch (err) {
      setMessage(`⚠️ Error: ${err}`);
    }
    setTimeout(() => setMessage(null), 3000);
  };

  return (
    <div className="relative p-4 border rounded bg-white shadow-md overflow-hidden">
      <h2 className="text-lg font-bold mb-2">🗺️ Container Map</h2>

      <svg className="absolute inset-0 w-full h-full z-0 pointer-events-none">
        {containers.map((source) =>
          source.connected.map((targetId) => {
            const from = positions[source.id];
            const to = positions[targetId];
            if (!from || !to) return null;
            return (
              <line
                key={`${source.id}->${targetId}`}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke="gray"
                strokeWidth="1.5"
                markerEnd="url(#arrow)"
              />
            );
          })
        )}
        <defs>
          <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L6,3 z" fill="gray" />
          </marker>
        </defs>
      </svg>

      {regions.map((region) => (
        <div key={region} className="mb-4">
          <h3 className="text-sm font-semibold mb-1">📦 {region}</h3>
          <div className="grid grid-cols-4 gap-4">
            {containers
              .filter((c) => (c.region || "Unassigned") === region)
              .map((c) => (
                <div
                  key={c.id}
                  ref={setContainerRef(c.id)}
                  onClick={() => handleTeleport(c.id)}
                  title={`ID: ${c.id} | Links: ${c.connected.join(", ")}`}
                  className={`p-2 border rounded text-sm cursor-pointer transition-all duration-150 select-none text-center
                    ${c.id === activeId ? "bg-blue-200 border-blue-500 font-bold scale-105" :
                      c.in_memory ? "bg-green-100" : "bg-gray-100"}`}
                >
                  <div>{c.name}</div>
                  {c.glyph && <div className="text-xs text-gray-500 mt-1">{c.glyph}</div>}
                </div>
              ))}
          </div>
        </div>
      ))}

      <div className="absolute bottom-2 right-2 bg-gray-50 p-2 rounded border text-xs">
        <strong>🧬 Glyph Minimap</strong>
        <div className="grid grid-cols-4 gap-1 mt-1 max-w-xs">
          {containers.map((c) => (
            <div
              key={`mini-${c.id}`}
              title={`${c.name} — ${c.glyph || "No glyph"}`}
              className={`w-4 h-4 border rounded-full ${c.id === activeId ? "bg-blue-400" : "bg-gray-300"}`}
            />
          ))}
        </div>
      </div>

      <p className="text-xs text-gray-500 mt-2">WebSocket: {connected ? "🟢 Connected" : "🔴 Disconnected"}</p>
      {message && <p className="text-sm mt-2 font-medium">{message}</p>}
    </div>
  );
}