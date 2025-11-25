// frontend/components/sci/SciBottomDock.tsx
import React, { useState } from "react";
import CoherenceStatus from "@/components/sci/CoherenceStatus";

const SciBottomDock: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"ai" | "logs">("ai");
  const [isOpen, setIsOpen] = useState(true);

  // collapsed pill
  if (!isOpen) {
    return (
      <button
        className="fixed bottom-2 left-1/2 z-30 -translate-x-1/2 rounded-t-md border border-border bg-background/90 px-3 py-1 text-xs text-foreground shadow-md"
        onClick={() => setIsOpen(true)}
      >
        ⬆ Open console
      </button>
    );
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-background/95 shadow-[0_-4px_12px_rgba(0,0,0,0.35)] backdrop-blur">
      {/* tab bar */}
      <div className="flex items-center justify-between px-3 py-1.5 text-xs">
        <div className="flex gap-1">
          <button
            onClick={() => setActiveTab("ai")}
            className={`rounded px-2 py-1 ${
              activeTab === "ai"
                ? "bg-primary text-primary-foreground"
                : "text-foreground/70 hover:bg-muted/60"
            }`}
          >
            AI
          </button>
          <button
            onClick={() => setActiveTab("logs")}
            className={`rounded px-2 py-1 ${
              activeTab === "logs"
                ? "bg-primary text-primary-foreground"
                : "text-foreground/70 hover:bg-muted/60"
            }`}
          >
            Logs
          </button>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="rounded px-2 py-1 text-[11px] text-foreground/70 hover:bg-muted/60"
        >
          ⬇ Hide
        </button>
      </div>

      {/* panel */}
      <div
        className="h-40 resize-y overflow-auto border-t border-border bg-background/98 px-4 py-3"
        style={{ minHeight: "6rem", maxHeight: "60vh" }}
      >
        {activeTab === "ai" ? (
          <div className="space-y-3 text-xs">
            {/* your snippet */}
            <CoherenceStatus />
            {/* future visual feed */}
            <div className="rounded-md border border-dashed border-slate-700/80 bg-slate-950/60 p-3 text-slate-400">
              Visual coherence feed will appear here.
            </div>
          </div>
        ) : (
          <div className="h-full text-xs text-slate-400">
            Runtime logs will show here.
          </div>
        )}
      </div>
    </div>
  );
};

export default SciBottomDock;