import React, { useEffect, useState } from "react";
import ContainerStatus from "@/components/AION/ContainerStatus";
import GlyphGrid from "@/components/AION/GlyphGrid";
import GlyphMutator from "@/components/AION/GlyphMutator";
import TessarisVisualizer from "@/components/AION/TessarisVisualizer";
import GlyphExecutor from "@/components/AION/GlyphExecutor";
import CommandBar from "@/components/CommandBar"; // ✅ Corrected path

export default function AvatarRuntimePage() {
  const [tick, setTick] = useState(0);
  const [glyphData, setGlyphData] = useState<string>(""); // Expecting glyph logic as a string
  const [cubes, setCubes] = useState<Record<string, any>>({});
  const [coord, setCoord] = useState<{ x: number; y: number; z: number; t: number }>({
    x: 0,
    y: 0,
    z: 0,
    t: 0,
  });
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState("");
  const [presets, setPresets] = useState<string[]>([]);
  const containerId = "default";

  useEffect(() => {
    const ws = new WebSocket("wss://comdex-api-kappa.vercel.app/ws/updates");
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "runtime_tick") {
          setTick(data.tick);
        } else if (data.type === "glyph_update") {
          setGlyphData(data.glyphs?.[0] || ""); // just use first glyph logic for now
          setCubes(data.cubes || {});
        }
      } catch (err) {
        console.error("WebSocket parse error:", err);
      }
    };
    ws.onerror = (e) => console.warn("WebSocket error:", e);
    ws.onclose = () => console.log("WebSocket closed");
    return () => ws.close();
  }, []);

  useEffect(() => {
    fetch("/api/aion/command/registry")
      .then((res) => res.json())
      .then((data) => {
        if (data.commands) {
          setPresets(data.commands.map((cmd: any) => cmd.command));
        }
      })
      .catch((err) => {
        console.warn("Failed to load command registry:", err);
      });
  }, []);

  const handleSubmit = async () => {
    if (!input.trim()) return;
    setLoading(true);
    try {
      const res = await fetch("/api/aion/command", {
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
    <div className="min-h-screen p-6 bg-gradient-to-b from-gray-100 to-white text-gray-900">
      <h1 className="text-3xl font-bold mb-6">🧠 AION Avatar Runtime</h1>

      {/* Container Map */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-semibold">🌐 Container Status</h2>
          <span className="text-sm text-gray-500">⏱️ Tick: {tick.toString().padStart(3, "0")}</span>
        </div>
        <ContainerStatus />
      </section>

      {/* Thought Tree */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-2">🧬 Tessaris Thought Tree</h2>
        <TessarisVisualizer />
      </section>

      {/* Glyph Grid + Mutator */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
        <div>
          <h2 className="text-xl font-semibold mb-2">🔠 Glyph Grid</h2>
          <GlyphGrid cubes={cubes} tick={tick} />
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

      {/* Execution Queue */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-2">⚡ Glyph Execution Queue</h2>
        <GlyphExecutor />
      </section>

      {/* Terminal */}
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
  );
}