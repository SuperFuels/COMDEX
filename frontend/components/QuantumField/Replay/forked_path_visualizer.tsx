import React from "react";
import { ArrowRight, GitBranch, Eye, Star } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ForkPathOption {
  tick: number;
  label: string;
  pathId: string;
  isCurrent?: boolean;
  isPrimary?: boolean;
  isPredicted?: boolean;
  isForked?: boolean;
  color?: string;
  score?: number; // Optional SQI or divergence score
}

interface ForkedPathVisualizerProps {
  paths: ForkPathOption[];
  onSelect: (pathId: string) => void;
  currentPathId: string;
}

export const ForkedPathVisualizer: React.FC<ForkedPathVisualizerProps> = ({
  paths,
  onSelect,
  currentPathId,
}) => {
  return (
    <div className="p-4 rounded-xl bg-black/80 text-white text-xs space-y-3 border border-white/20 max-w-sm shadow-md">
      <h2 className="text-sm font-bold flex items-center gap-2 text-white/90">
        <GitBranch size={14} /> Forked Paths
      </h2>

      <ul className="space-y-2">
        {paths.map((path) => {
          const rowClasses = cn(
            "flex items-center justify-between p-2 rounded cursor-pointer transition-colors duration-150",
            path.pathId === currentPathId
              ? "bg-indigo-700 text-white ring-2 ring-indigo-400"
              : "bg-gray-800 hover:bg-gray-700"
          );

          return (
            <li
              key={path.pathId}
              className={rowClasses}
              onClick={() => onSelect(path.pathId)}
              style={{ borderLeft: `4px solid ${path.color ?? "#888"}` }}
            >
              <div className="flex items-center gap-2">
                {path.isPrimary && (
                  <>
                    <ArrowRight size={12} className="text-green-400" aria-label="Primary Path" />
                    <span className="sr-only">Primary Path</span>
                  </>
                )}
                {path.isPredicted && (
                  <>
                    <Eye size={12} className="text-yellow-400" aria-label="Predicted Path" />
                    <span className="sr-only">Predicted Path</span>
                  </>
                )}
                {path.isForked && (
                  <>
                    <Star size={12} className="text-pink-400" aria-label="Forked / Divergent" />
                    <span className="sr-only">Forked / Divergent</span>
                  </>
                )}
                <span className="font-semibold">{path.label}</span>
              </div>

              <div className="text-white/70 flex gap-2 items-center">
                {typeof path.score === "number" && (
                  <span className="text-cyan-400">SQI: {Math.round(path.score * 100)}%</span>
                )}
                <span>⏱ Tick {path.tick}</span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
};