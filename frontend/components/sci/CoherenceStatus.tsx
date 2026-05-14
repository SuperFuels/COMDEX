// frontend/components/sci/CoherenceStatus.tsx
import React from "react";

type CoherenceStatusProps = {
  phi?: number;
  coherence?: number;
  status?: "connected" | "disconnected" | "ready";
};

const CoherenceStatus: React.FC<CoherenceStatusProps> = ({
  phi = 0,
  coherence = 0,
  status = "disconnected",
}) => {
  const label =
    status === "connected"
      ? "Connected"
      : status === "ready"
      ? "Ready"
      : "Disconnected";

  const badgeColor =
    status === "connected"
      ? "text-emerald-400"
      : status === "ready"
      ? "text-sky-400"
      : "text-amber-300";

  return (
    <div className="flex items-center justify-between rounded-md border border-slate-700 bg-slate-950/70 px-3 py-2 text-xs text-slate-200">
      <div className="flex flex-col">
        <span className="text-[11px] uppercase tracking-wide text-slate-400">
          Φ coherence
        </span>
        <span className="text-sm font-semibold">
          Φ {phi.toFixed(3)} · coherence {coherence.toFixed(3)}
        </span>
      </div>
      <span
        className={`rounded-full border border-slate-600 px-2 py-1 text-[11px] ${badgeColor}`}
      >
        {label}
      </span>
    </div>
  );
};

export default CoherenceStatus;