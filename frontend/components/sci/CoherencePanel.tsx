// frontend/components/sci/CoherencePanel.tsx
import React from "react";

export interface CoherencePanelProps {
  phi: number;
  coherence: number;
  status?: "connected" | "disconnected";
}

export const CoherencePanel: React.FC<CoherencePanelProps> = ({
  phi,
  coherence,
  status = "disconnected",
}) => {
  const statusLabel = status === "connected" ? "Connected" : "Disconnected";

  return (
    <div className="flex flex-col gap-3 text-xs text-slate-200">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-baseline gap-1 font-mono">
          <span className="text-sm">Φ</span>
          <span className="text-lg">{phi.toFixed(3)}</span>
        </div>
        <span className="text-slate-400">
          coherence: {coherence.toFixed(3)}
        </span>
        <span
          className={
            status === "connected"
              ? "text-emerald-400"
              : "text-amber-400 flex items-center gap-1"
          }
        >
          <span className="inline-block h-2 w-2 rounded-full bg-current" />
          {statusLabel}
        </span>
      </div>

      {/* placeholder area for future visual feed */}
      <div className="mt-1 flex h-24 items-center justify-center rounded-md border border-border bg-background/40 text-[11px] text-slate-500">
        Coherence visual feed (coming soon)
      </div>
    </div>
  );
};

export default CoherencePanel;