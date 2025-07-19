import React, { useEffect, useState } from "react";
import {
  ArrowBigRight,
  BookOpenCheck,
  Clock,
  TimerReset,
  Filter,
  Play,
  SkipForward,
  Info,
  Eye,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

type BranchNode = {
  id: string;
  symbol: string;
  value?: string;
  children?: BranchNode[];
  mutated?: boolean;
  info?: string;
};

type TriggerTrace = {
  timestamp: string;
  glyph: string;
  context: Record<string, any>;
  memory_links: string[];
  reason?: string;
  created_at?: string;
};

type MemoryEntry = {
  id: string;
  role: string;
  content: string;
  created_at: string;
};

interface TessarisVisualizerProps {
  tree: BranchNode | null;
  onNodeClick?: (node: BranchNode) => void;
}

const Card = ({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) => (
  <div className={cn("rounded border bg-white shadow p-4", className)}>
    {children}
  </div>
);

export default function TessarisVisualizer({ tree, onNodeClick }: TessarisVisualizerProps) {
  const [traces, setTraces] = useState<TriggerTrace[]>([]);
  const [filter, setFilter] = useState({
    glyph: "",
    minAge: 0,
    maxAge: 600,
  });
  const [replayIndex, setReplayIndex] = useState<number | null>(null);
  const [memoryTrace, setMemoryTrace] = useState<MemoryEntry[] | null>(null);

  useEffect(() => {
    fetch("/api/aion/memory-trace")
      .then((res) => res.json())
      .then((data) => setTraces(data?.traces ?? []));
  }, []);

  useEffect(() => {
    if (replayIndex !== null && traces[replayIndex]) {
      fetch(`/api/aion/memory?id=${traces[replayIndex].glyph}`)
        .then((res) => res.json())
        .then((data) => setMemoryTrace(data?.memory ?? []));
    }
  }, [replayIndex]);

  const getAge = (created_at?: string): number | null => {
    if (!created_at) return null;
    const ageMs = Date.now() - new Date(created_at).getTime();
    return Math.floor(ageMs / 1000);
  };

  const getAgeColor = (age: number) => {
    if (age < 30) return "bg-green-300";
    if (age < 90) return "bg-yellow-300";
    return "bg-red-300";
  };

  const renderBranch = (node: BranchNode, depth = 0) => {
    const age = traces.find((t) => t.glyph === node.symbol)?.created_at;
    const ageSec = getAge(age ?? "");
    const pulse = ageSec !== null && ageSec < 10;

    return (
      <motion.div
        key={node.id}
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.2 + depth * 0.05 }}
        className={cn(
          "pl-4 relative mb-2 group",
          pulse && "animate-pulse",
          node.mutated && "ring-2 ring-pink-400"
        )}
        data-glyph={node.symbol}
        onClick={() => onNodeClick?.(node)}
      >
        <motion.div
          whileHover={{ scale: 1.04 }}
          className="flex items-center space-x-2"
        >
          <ArrowBigRight
            className={cn(
              "w-4 h-4 transition-all",
              depth === 0 && "text-green-500",
              depth === 1 && "text-blue-400",
              depth >= 2 && "text-purple-400"
            )}
          />
          <motion.div
            initial={{ scale: 0.95 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.3 }}
            className="relative flex items-center"
          >
            <span className="font-mono text-sm font-semibold text-blue-700">
              {node.symbol}
            </span>
            {node.value && (
              <span className="ml-2 text-xs font-mono text-gray-600">
                ⟶ {node.value}
              </span>
            )}
            {node.info && (
              <div
                className="ml-2 w-4 h-4 text-gray-400 hover:text-blue-500 cursor-pointer"
                title={node.info}
              >
                <Info className="w-full h-full" />
              </div>
            )}
          </motion.div>
        </motion.div>

        {node.children && node.children.length > 0 && (
          <motion.div
            initial={{ opacity: 0, scaleY: 0.95 }}
            animate={{ opacity: 1, scaleY: 1 }}
            transition={{ duration: 0.25 }}
            className="ml-4 border-l border-border pl-4 origin-top"
          >
            {node.children.map((child) => renderBranch(child, depth + 1))}
          </motion.div>
        )}
      </motion.div>
    );
  };

  const filteredTraces = traces.filter((t) => {
    const age = getAge(t.created_at);
    const matchGlyph =
      filter.glyph.trim() === "" ||
      t.glyph.toLowerCase().includes(filter.glyph.toLowerCase());
    const withinAge =
      age !== null && age >= filter.minAge && age <= filter.maxAge;
    return matchGlyph && withinAge;
  });

  const stepReplay = () => {
    if (filteredTraces.length === 0) return;
    setReplayIndex((prev) => {
      if (prev === null || prev >= filteredTraces.length - 1) return 0;
      return prev + 1;
    });
  };

  return (
    <Card className="max-h-[80vh] overflow-auto">
      <h2 className="text-xl font-bold mb-3">🧠 Tessaris Thought Tree</h2>
      <AnimatePresence initial={false}>
        {tree ? (
          renderBranch(tree)
        ) : (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-muted-foreground text-sm"
          >
            Loading tree...
          </motion.p>
        )}
      </AnimatePresence>

      <hr className="my-4" />

      <div className="flex justify-between items-center mb-2">
        <h3 className="text-md font-semibold">🧬 Glyph Trigger Trace</h3>
        <button
          className="text-xs bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded flex items-center"
          onClick={stepReplay}
        >
          <SkipForward className="w-3 h-3 mr-1" /> Step
        </button>
      </div>

      <div className="mb-3 text-sm flex items-center space-x-2">
        <Filter className="w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          className="border px-2 py-1 text-xs rounded w-32"
          placeholder="Glyph filter"
          value={filter.glyph}
          onChange={(e) => setFilter({ ...filter, glyph: e.target.value })}
        />
        <input
          type="number"
          className="border px-2 py-1 text-xs rounded w-20"
          placeholder="Min age"
          value={filter.minAge}
          onChange={(e) =>
            setFilter({ ...filter, minAge: Number(e.target.value) })
          }
        />
        <input
          type="number"
          className="border px-2 py-1 text-xs rounded w-20"
          placeholder="Max age"
          value={filter.maxAge}
          onChange={(e) =>
            setFilter({ ...filter, maxAge: Number(e.target.value) })
          }
        />
      </div>

      <AnimatePresence initial={false}>
        {filteredTraces.length > 0 ? (
          filteredTraces.map((trace, index) => {
            const age = getAge(trace.created_at);
            const percent = age ? Math.min(age / filter.maxAge, 1) * 100 : 0;
            const isActive = replayIndex === index;

            return (
              <motion.div
                layout
                key={index}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 4 }}
                transition={{ duration: 0.2 }}
                className={cn(
                  "mb-3 border rounded p-2 transition",
                  isActive
                    ? "border-blue-500 bg-blue-50"
                    : "border-border bg-gray-50"
                )}
                data-trace={trace.glyph}
              >
                <div className="flex justify-between items-center mb-1">
                  <div className="flex items-center space-x-2">
                    <Clock className="w-4 h-4 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">
                      {trace.timestamp}
                    </span>
                    {age !== null && (
                      <span className="text-xs text-gray-600 flex items-center space-x-1 ml-2">
                        <TimerReset className="w-3 h-3" /> <span>{age}s</span>
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-1">
                    <button
                      className="text-xs px-1 py-0.5 rounded bg-blue-100 hover:bg-blue-200"
                      onClick={() => setReplayIndex(index)}
                    >
                      <Play className="w-3 h-3 inline-block mr-1" /> Replay
                    </button>
                  </div>
                </div>

                <div className="flex items-center mt-1 space-x-2">
                  <BookOpenCheck className="w-4 h-4 text-blue-600" />
                  <span className="font-mono text-sm">
                    Glyph <strong>{trace.glyph}</strong>
                  </span>
                </div>

                {trace.reason && (
                  <div className="text-xs mt-1 italic text-indigo-600">
                    🧠 Trigger Reason: {trace.reason}
                  </div>
                )}

                {age !== null && (
                  <div className="mt-2 w-full bg-gray-200 rounded h-2">
                    <div
                      className={`${getAgeColor(age)} h-2 rounded`}
                      style={{ width: `${percent}%` }}
                    ></div>
                  </div>
                )}

                <div className="text-xs mt-2">
                  <strong>Context:</strong>{" "}
                  <code className="text-[10px] bg-muted px-1 py-0.5 rounded">
                    {JSON.stringify(trace.context)}
                  </code>
                </div>

                {trace.memory_links?.length > 0 && (
                  <div className="text-xs mt-1">
                    <strong>Memory Links:</strong>
                    <ul className="list-disc ml-5">
                      {trace.memory_links.map((link, i) => (
                        <li key={i} className="text-[11px]">
                          {link}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {isActive && memoryTrace && (
                  <div className="mt-3">
                    <h4 className="text-xs font-bold text-gray-500 mb-1 flex items-center">
                      <Eye className="w-3 h-3 mr-1" /> Memory Trace
                    </h4>
                    <ul className="text-xs bg-gray-100 rounded p-2 space-y-1">
                      {memoryTrace.map((entry) => (
                        <li key={entry.id} className="text-[11px]">
                          <strong>{entry.role}:</strong> {entry.content}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </motion.div>
            );
          })
        ) : (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-muted-foreground text-sm"
          >
            No glyph traces match the filters.
          </motion.p>
        )}
      </AnimatePresence>
    </Card>
  );
}