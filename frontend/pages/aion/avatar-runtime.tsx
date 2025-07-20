// pages/aion/avatar-runtime.tsx

import React, { useEffect, useState, useRef } from "react";
import ContainerStatus from "@/components/AION/ContainerStatus";
import GlyphGrid from "@/components/AION/GlyphGrid";
import GlyphMutator from "@/components/AION/GlyphMutator";
import TessarisVisualizer from "@/components/AION/TessarisVisualizer";
import TessarisIntentVisualizer from "@/components/AION/TessarisIntentVisualizer";
import TessarisTracePanel from "@/components/AION/TessarisTracePanel";
import GlyphExecutor from "@/components/AION/GlyphExecutor";
import CommandBar from "@/components/CommandBar";
import GlyphQROverlay from "@/components/AION/GlyphQROverlay";
import GlyphSummaryHUD from "@/components/AION/GlyphSummaryHUD";
import TimelineControls from "@/components/AION/TimelineControls";
import GlyphTriggerEditor from "@/components/AION/GlyphTriggerEditor";
import GlyphCompressorPanel from "@/components/AION/GlyphCompressorPanel";

type ViewMode = "top-down" | "3d-symbolic" | "glyph-logic";

const getWssUrl = (path: string) => {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || '';
  const wsProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';
  const base = apiBase.replace(/^https?:\/\//, `${wsProtocol}://`).replace(/\/api\/?$/, '');
  return `${base}${path}`;
};

export default function AvatarRuntimePage() {
  const [tick, setTick] = useState(0);
  const [glyphData, setGlyphData] = useState<string>("");
  const [cubes, setCubes] = useState<Record<string, any>>({});
  const [prevCubes, setPrevCubes] = useState<Record<string, any>>({});
  const [glyphDiff, setGlyphDiff] = useState<any>(null);
  const [coord, setCoord] = useState({ x: 0, y: 0, z: 0, t: 0 });
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState("");
  const [presets, setPresets] = useState<string[]>([]);
  const [showQR, setShowQR] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("top-down");
  const [timeRatio, setTimeRatio] = useState(1);
  const [isPlaying, setIsPlaying] = useState(false);
  const containerId = "default";

  const playbackInterval = useRef<NodeJS.Timeout | null>(null);

  const diffGlyphs = (oldCubes: any, newCubes: any) => {
    const added: string[] = [];
    const removed: string[] = [];
    const changed: string[] = [];

    const allKeys = new Set([...Object.keys(oldCubes || {}), ...Object.keys(newCubes || {})]);

    for (const key of allKeys) {
      const oldCube = oldCubes?.[key] ?? {};
      const newCube = newCubes?.[key] ?? {};
      const oldGlyph = oldCube?.glyph ?? "";
      const newGlyph = newCube?.glyph ?? "";

      if (!oldGlyph && newGlyph) added.push(key);
      else if (oldGlyph && !newGlyph) removed.push(key);
      else if (oldGlyph !== newGlyph) changed.push(key);
    }

    return { added, removed, changed };
  };

  const fetchSnapshot = async (targetTick: number) => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/glyphs?t=${targetTick}`);
      const data = await res.json();
      if (data?.cubes) {
        setPrevCubes(cubes);
        setCubes(data.cubes);
        const diff = diffGlyphs(cubes, data.cubes);
        setGlyphDiff(diff);
      }
    } catch (err) {
      console.error("Failed to fetch rewind snapshot:", err);
    }
  };

  const handlePlay = () => {
    setIsPlaying(true);
    playbackInterval.current = setInterval(() => {
      setTick((prev) => {
        const next = prev + 1;
        fetchSnapshot(next);
        return next;
      });
    }, 1000);
  };

  const handlePause = () => {
    setIsPlaying(false);
    if (playbackInterval.current) clearInterval(playbackInterval.current);
  };

  const handlePrev = () => {
    setTick((prev) => {
      const next = Math.max(0, prev - 1);
      fetchSnapshot(next);
      return next;
    });
  };

  const handleNext = () => {
    setTick((prev) => {
      const next = prev + 1;
      fetchSnapshot(next);
      return next;
    });
  };

  useEffect(() => {
    const ws = new WebSocket(getWssUrl("/ws/updates"));

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "runtime_tick") {
          setTick(data.tick ?? 0);
        } else if (data.type === "glyph_update") {
          setGlyphData(data?.glyphs?.[0] ?? "");
          const newCubes = data?.cubes ?? {};
          setPrevCubes(cubes);
          setCubes(newCubes);
          const diff = diffGlyphs(cubes, newCubes);
          setGlyphDiff(diff);
        }
      } catch (err) {
        console.error("WebSocket parse error:", err);
      }
    };

    ws.onerror = (e) => console.warn("WebSocket error:", e);
    ws.onclose = () => console.log("WebSocket closed");

    return () => ws.close();
  }, [cubes]);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/aion/command/registry`)
      .then((res) => res.json())
      .then((data) => {
        if (data?.commands) {
          setPresets(data.commands.map((cmd: any) => cmd.command));
        }
      })
      .catch((err) => {
        console.warn("Failed to load command registry:", err);
      });
  }, []);

  useEffect(() => {
    return () => {
      if (playbackInterval.current) clearInterval(playbackInterval.current);
    };
  }, []);

  const handleSubmit = async () => {
    if (!input.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/aion/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: input }),
      });
      const data = await res.json();
      console.log("Command result:", data);
    } catch (err) {
      console.error("Command failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleMutationComplete = () => {
    console.log("Mutation completed");
  };

  return (
    <div className="min-h-screen p-6 bg-gradient-to-b from-gray-100 to-white text-gray-900 flex">
      <div className="flex-1 pr-4">
        <h1 className="text-3xl font-bold mb-6">🧠 AION Avatar Runtime</h1>

        <section className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xl font-semibold">🌐 Container Status</h2>
            <span className="text-sm text-gray-500">⏱️ Tick: {tick.toString().padStart(3, "0")}</span>
          </div>
          <ContainerStatus />
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-2">🧬 Tessaris Thought Tree</h2>
          <TessarisVisualizer tree={{ id: "root", symbol: "🌱", children: [] }} />
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-2">🧩 Tessaris Intents</h2>
          <TessarisIntentVisualizer />
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-2">📜 Tessaris Execution Trace</h2>
          <TessarisTracePanel />
        </section>

        <section className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
          <div>
            <div className="flex justify-between items-center mb-2">
              <h2 className="text-xl font-semibold">🔠 Glyph Grid</h2>
              <div className="flex space-x-2">
                <select
                  value={viewMode}
                  onChange={(e) => setViewMode(e.target.value as ViewMode)}
                  className="border rounded p-1 text-sm"
                >
                  <option value="top-down">Top-Down View</option>
                  <option value="3d-symbolic">3D Symbolic View</option>
                  <option value="glyph-logic">CodexLang / GlyphOS Logic</option>
                </select>
                <button
                  onClick={() => setShowQR(!showQR)}
                  className="px-3 py-1 text-sm bg-purple-600 text-white rounded-md hover:bg-purple-700 transition"
                >
                  {showQR ? "Hide QR" : "Show GlyphQR"}
                </button>
              </div>
            </div>
            <GlyphGrid cubes={cubes} tick={tick} viewMode={viewMode} />
            {showQR && (
              <div className="mt-4">
                <GlyphQROverlay glyphData={glyphData} visible={true} />
              </div>
            )}
          </div>
          <div>
            <h2 className="text-xl font-semibold mb-2">🧪 Glyph Mutator</h2>
            <GlyphMutator
              containerId={containerId}
              coord={`${coord.x},${coord.y},${coord.z},${coord.t}`}
              glyphData={glyphData}
              onMutationComplete={handleMutationComplete}
            />
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-2">⚡ Glyph Execution Queue</h2>
          <GlyphExecutor />
        </section>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-2">📺 Glyph Runtime HUD</h2>
          <GlyphSummaryHUD glyphDiff={glyphDiff} />
        </section>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-2">📺 Timeline Playback</h2>
          <TimelineControls
            isPlaying={isPlaying}
            currentTick={tick}
            onPlay={handlePlay}
            onPause={handlePause}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        </section>

        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-2">🕰️ Container Time Ratio</h2>
          <div className="flex items-center space-x-4">
            <input
              type="range"
              min={0.1}
              max={5}
              step={0.1}
              value={timeRatio}
              onChange={(e) => setTimeRatio(Number(e.target.value))}
              className="w-48"
            />
            <span className="text-sm text-gray-700">Ratio: {timeRatio.toFixed(1)}x</span>
          </div>
        </section>

        <section className="border-t border-gray-300 pt-6 mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h2 className="text-lg font-medium mb-2">🧭 AION Command Interface</h2>
            <CommandBar
              input={input}
              setInput={setInput}
              loading={loading}
              onSubmit={handleSubmit}
              presets={presets}
              setInputFromPreset={(value: string) => setInput(value)}
            />
          </div>
          <div>
            <h2 className="text-lg font-medium mb-2">💬 GPT Prompt Console</h2>
            <div className="p-4 border rounded-md text-sm text-gray-600 bg-gray-50">
              GPT prompt interface is not available in this view.
            </div>
          </div>
        </section>
      </div>

      <div className="w-96 border-l border-gray-300 bg-white shadow-inner flex flex-col overflow-y-auto">
        <GlyphTriggerEditor />
        <div className="border-t border-gray-200 mt-4 pt-4">
          <GlyphCompressorPanel />
        </div>
      </div>
    </div>
  );
}