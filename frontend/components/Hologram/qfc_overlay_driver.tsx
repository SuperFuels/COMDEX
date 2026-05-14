// frontend/components/Hologram/QFCOverlayDriver.tsx
'use client';

import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';

// ---------- Types ----------
interface SymbolicNode {
  id: string;
  label: string;
  type: string;
  depth: number;
  position: { x: number; y: number; z: number };
  morphic_overlay?: any;
  glyph_id?: string;
  entangled_ids?: string[];
  agent_id?: string;
  qglyph?: any;
  children?: SymbolicNode[];
}

interface TrailOverlayMetadata {
  label: string;
  concept_match_score?: number;
  semantic_distance?: number;
  intensity?: number;
}

interface SymbolicTree {
  tree_id: string;
  root: SymbolicNode;
  timestamp: string;
  metadata: Record<string, any>;
  fusion_enabled: boolean;
  supports_replay: boolean;
  symbolnetOverlay?: TrailOverlayMetadata[];
}

interface QFCOverlayDriverProps {
  containerId: string;
}

// ---------- Helpers ----------
function flattenTree(root: SymbolicNode | null | undefined): SymbolicNode[] {
  if (!root) return [];
  const out: SymbolicNode[] = [];
  const stack: SymbolicNode[] = [root];
  while (stack.length) {
    const n = stack.pop()!;
    out.push(n);
    if (n.children?.length) {
      // push children in reverse so first child appears next in the array
      for (let i = n.children.length - 1; i >= 0; i--) stack.push(n.children[i]);
    }
  }
  return out;
}

// ---------- Component ----------
export default function QFCOverlayDriver({ containerId }: QFCOverlayDriverProps) {
  const [tree, setTree] = useState<SymbolicTree | null>(null);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await axios.get(`/api/qfc/holographic_tree/${containerId}`);
        const fetched: SymbolicTree | null = res?.data?.tree ?? null;
        if (alive) setTree(fetched);
      } catch (err) {
        console.error('[QFCOverlayDriver] Failed to load tree:', err);
      }
    })();
    return () => {
      alive = false;
    };
  }, [containerId]);

  const nodes = useMemo(() => flattenTree(tree?.root), [tree]);
  const current = nodes[index] || null;

  // Keep index in range if data refreshes
  useEffect(() => {
    if (index >= nodes.length) setIndex(Math.max(0, nodes.length - 1));
  }, [nodes.length, index]);

  if (!tree) {
    return (
      <div className="text-sm text-gray-400 p-3">
        Loading symbolic overlay…
      </div>
    );
  }

  return (
    <div className="qfc-overlay-container relative w-full h-full p-3 space-y-3 bg-black/30 rounded-lg">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-white/80">
          QFC Tree: <span className="font-mono">{tree.tree_id}</span>
        </div>
        <div className="text-xs text-white/60">
          Nodes: <span className="font-mono">{nodes.length}</span> •
          Timestamp: <span className="font-mono ml-1">{tree.timestamp}</span>
        </div>
      </div>

      {/* Slider */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-white/70 w-28">Navigate Nodes</span>
        <input
          type="range"
          min={0}
          max={Math.max(0, nodes.length - 1)}
          step={1}
          value={index}
          onChange={(e) => setIndex(Number(e.target.value))}
          className="w-full"
        />
        <span className="text-xs text-white/70 w-24 text-right font-mono">
          {nodes.length ? `${index + 1}/${nodes.length}` : '0/0'}
        </span>
      </div>

      {/* Current Node Card */}
      {current ? (
        <div className="rounded-md border border-white/10 bg-black/50 p-3 text-sm text-white/90">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <div className="font-semibold">{current.label || '(unnamed node)'}</div>
            <div className="px-2 py-0.5 rounded bg-white/10 text-xs">
              {current.type} • depth {current.depth}
            </div>
            {current.agent_id && (
              <div className="px-2 py-0.5 rounded bg-purple-700/40 text-xs">
                agent: {current.agent_id}
              </div>
            )}
          </div>

          <div className="mt-2 grid grid-cols-2 gap-3 text-xs text-white/80">
            <div>
              <div className="text-white/50">Node ID</div>
              <div className="font-mono break-all">{current.id}</div>
            </div>
            <div>
              <div className="text-white/50">Glyph ID</div>
              <div className="font-mono break-all">{current.glyph_id ?? '—'}</div>
            </div>
            <div>
              <div className="text-white/50">Position</div>
              <div className="font-mono">
                [{current.position.x.toFixed(2)}, {current.position.y.toFixed(2)},{' '}
                {current.position.z.toFixed(2)}]
              </div>
            </div>
            <div>
              <div className="text-white/50">Entangled</div>
              <div className="font-mono">
                {current.entangled_ids?.length ?? 0}
              </div>
            </div>
          </div>

          {/* Overlay metadata preview (if provided) */}
          {tree.symbolnetOverlay?.length ? (
            <div className="mt-3">
              <div className="text-white/60 text-xs mb-1">SymbolNet Overlay</div>
              <div className="flex flex-wrap gap-2">
                {tree.symbolnetOverlay.slice(0, 6).map((m, i) => (
                  <div
                    key={`${m.label}-${i}`}
                    className="px-2 py-1 rounded bg-white/10 text-xs"
                    title={JSON.stringify(m)}
                  >
                    {m.label}
                    {typeof m.concept_match_score === 'number' && (
                      <span className="ml-1 text-white/60">
                        ({m.concept_match_score.toFixed(2)})
                      </span>
                    )}
                  </div>
                ))}
                {tree.symbolnetOverlay.length > 6 && (
                  <div className="px-2 py-1 rounded bg-white/5 text-white/60 text-xs">
                    +{tree.symbolnetOverlay.length - 6} more
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <div className="rounded-md border border-white/10 bg-black/50 p-3 text-sm text-white/70">
          No node selected.
        </div>
      )}
    </div>
  );
}