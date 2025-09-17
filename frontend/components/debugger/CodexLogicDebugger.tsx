// 📁 frontend/components/debugger/CodexLogicDebugger.tsx
"use client";

import React, { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

type TraceEntry = {
  glyph: string;
  action?: string;
  result?: string;
  timestamp: number;
  source?: string;
  predicted?: boolean;
  confidence?: number;
  entropy?: number;
  detail?: any;
};

type DebuggerProps = {
  containerId: string;
};

export const CodexLogicDebugger: React.FC<DebuggerProps> = ({ containerId }) => {
  const [trace, setTrace] = useState<TraceEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const loadTrace = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/codex/trace?containerId=${encodeURIComponent(containerId)}`);
      const data = await res.json();
      setTrace(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error("Failed to load trace:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTrace();
  }, [containerId]);

  return (
    <Card className="w-full p-2 rounded-2xl shadow-xl bg-background/90 border border-muted">
      <CardContent>
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-lg font-semibold">🧠 Codex Logic Debugger</h3>

          {/* no size/variant props -> style via className */}
          <Button
            onClick={loadTrace}
            disabled={loading}
            className={cn(
              "h-8 px-3 text-sm border border-border bg-transparent",
              "hover:bg-muted/40 disabled:opacity-60 disabled:cursor-not-allowed"
            )}
          >
            <Loader2
              className={cn("w-4 h-4 mr-1", loading && "animate-spin")}
              aria-hidden="true"
            />
            Refresh
          </Button>
        </div>

        <ScrollArea className="h-[400px] pr-2">
          {trace.map((entry, idx) => (
            <div
              key={idx}
              className={cn(
                "p-2 mb-2 rounded-md border transition-all",
                entry.predicted
                  ? "bg-yellow-100/60 border-yellow-400"
                  : "bg-white border-gray-300"
              )}
            >
              <div className="flex justify-between items-center">
                <span className="text-sm font-mono">
                  🌀 {entry.glyph}
                  {entry.predicted && " (Predicted)"}
                </span>
                <span className="text-xs text-muted-foreground">
                  {new Date(entry.timestamp * 1000).toLocaleTimeString()}
                </span>
              </div>

              {entry.action && (
                <div className="text-xs mt-1 text-muted-foreground">
                  Action: {entry.action}
                  {entry.result && <> → Result: {entry.result}</>}
                </div>
              )}

              {entry.confidence !== undefined && (
                <div className="text-xs mt-1">
                  Confidence: <b>{(entry.confidence * 100).toFixed(1)}%</b>
                  {" — "}
                  Entropy: <b>{entry.entropy?.toFixed(3)}</b>
                </div>
              )}

              {entry.detail?.candidates && (
                <div className="text-xs mt-1 italic text-muted-foreground">
                  Candidates: {entry.detail.candidates.join(", ")}
                </div>
              )}
            </div>
          ))}
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export default CodexLogicDebugger;