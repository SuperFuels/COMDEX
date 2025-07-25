// File: frontend/components/GlyphNet/GlyphNetTerminal.tsx

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import useWebSocket from "@/hooks/useWebSocket";

export default function GlyphNetTerminal() {
  const [command, setCommand] = useState("");
  const [log, setLog] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  // ✅ Handle messages from backend
  const { emit } = useWebSocket("/ws/glyphnet", (msg: any) => {
    const message = typeof msg === "string" ? msg : JSON.stringify(msg);
    setLog((prev) => [`📩 ${message}`, ...prev]);
  });

  const handleRun = async () => {
    const trimmed = command.trim();
    if (!trimmed) return;

    try {
      const [_, glyph, target] = trimmed.match(/send (.+) to (.+)/i) || [];
      if (glyph && target) {
        const packet = {
          type: "symbolic_thought",
          glyphs: [{ glyph }],
          meta: { container: target, from: "terminal", command },
        };
        emit("glyphnet_command", { command: trimmed, packet });
        setLog((prev) => [`✅ Sent: ${glyph} → ${target}`, ...prev]);
        setCommand("");
        return;
      }

      // ⌘ CodexLang command
      setLoading(true);
      const res = await fetch("/api/glyphnet/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: trimmed }),
      });
      const data = await res.json();
      if (data.status === "ok") {
        setLog((prev) => [`🧠 Executed: ${trimmed}`, ...prev]);
      } else {
        setLog((prev) => [`⚠️ ${data.message}`, ...prev]);
      }
      setCommand("");
    } catch (err) {
      setLog((prev) => [`❌ ${(err as Error).message}`, ...prev]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full">
      <CardContent>
        <h2 className="text-lg font-bold mb-2">⌨️ GlyphNet Terminal</h2>
        <div className="flex gap-2 mb-2">
          <Input
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder='Try: send ↔ to container:main OR ⌘ ⟦ Thought : Reflect ⟧'
            className="w-3/4"
            onKeyDown={(e) => e.key === "Enter" && handleRun()}
          />
          <Button onClick={handleRun} disabled={loading}>
            {loading ? "Running..." : "Run"}
          </Button>
        </div>
        <Textarea
          readOnly
          value={log.join("\n")}
          className="text-xs h-40 font-mono bg-black text-green-400"
        />
      </CardContent>
    </Card>
  );
}