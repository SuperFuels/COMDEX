import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowUpRight, GitBranch, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

interface ForkScore {
  waveId: string;
  parentWaveId: string;
  score: number;
  glow: number;
  pulse: number;
  mutationCause: string;
  timestamp: number; // seconds
}

interface InnovationScoreOverlayProps {
  forks: ForkScore[];
  onReplayFork?: (waveId: string) => void;
}

function timeAgo(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp * 1000) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

export const InnovationScoreOverlay: React.FC<InnovationScoreOverlayProps> = ({
  forks,
  onReplayFork,
}) => {
  return (
    <div className="fixed top-4 right-4 w-[360px] max-h-[85vh] overflow-y-auto z-50 space-y-3">
      <div className="text-lg font-semibold text-primary px-2 pt-1">🧠 Innovation Forks</div>

      {forks.length === 0 ? (
        <div className="text-sm text-muted-foreground px-4 pt-2">No forks yet.</div>
      ) : (
        forks.map((fork) => {
          const borderColor = `rgba(255, 200, 0, ${Math.min(1, fork.score / 5)})`;
          const boxShadow = `0 0 ${fork.glow}px rgba(255, 200, 0, 0.5)`;

          return (
            <motion.div
              key={fork.waveId}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              {/* style on wrapper to avoid typing issues on Card */}
              <div style={{ borderColor, boxShadow }} className="rounded-2xl border-2">
                <Card className="bg-background rounded-2xl shadow-xl">
                  <CardContent className="p-4 space-y-2">
                    {/* Optional tiny meta line instead of title prop */}
                    <div className="text-[11px] text-muted-foreground/70">
                      Cause: {fork.mutationCause} • Parent: {fork.parentWaveId.slice(0, 8)}
                    </div>

                    <div className="flex justify-between items-center">
                      <div className="font-semibold text-sm text-muted-foreground">Fork ID</div>
                      <Badge className="text-xs">{fork.waveId.slice(0, 8)}</Badge>
                    </div>

                    <div className="text-sm flex items-center gap-1">
                      <Sparkles className="w-4 h-4 text-yellow-500" />
                      <span className="font-medium">Innovation Score:</span>{" "}
                      {fork.score.toFixed(3)}
                    </div>

                    <div className="text-sm flex gap-2">
                      <span className="text-muted-foreground">Glow:</span>
                      <span className="font-mono text-accent-foreground">{fork.glow}</span>
                      <span className="text-muted-foreground">Pulse:</span>
                      <span className="font-mono text-accent-foreground">{fork.pulse}</span>
                    </div>

                    <div className="text-xs text-muted-foreground">{timeAgo(fork.timestamp)}</div>

                    <div className="flex justify-end gap-2 pt-2">
                      {onReplayFork && (
                        <Button
                          onClick={() => onReplayFork(fork.waveId)}
                          className="h-7 px-2 text-xs bg-transparent hover:bg-muted/40"
                        >
                          <GitBranch className="w-3 h-3 mr-1" /> Replay
                        </Button>
                      )}
                      <Button
                        className="h-7 px-2 text-xs border border-border hover:bg-muted/30"
                        onClick={() => navigator.clipboard.writeText(fork.waveId)}
                      >
                        <ArrowUpRight className="w-3 h-3 mr-1" /> Copy ID
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </motion.div>
          );
        })
      )}
    </div>
  );
};