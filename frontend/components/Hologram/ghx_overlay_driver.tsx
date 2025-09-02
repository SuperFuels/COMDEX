import { useEffect, useRef, useState } from 'react';
import type { SymbolicNode } from '../../lib/types/symbolic_types';
import { fetchHolographicTree } from '@/lib/hologram/holographic_api';
import { renderSymbolicTrail } from '../../lib/hologram/ghx_trail_renderer';

interface GHXOverlayDriverProps {
  containerId: string;
  hoveredNodeId?: string | null;
}

export default function GHXOverlayDriver({
  containerId,
  hoveredNodeId = null,
}: GHXOverlayDriverProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [treeData, setTreeData] = useState<SymbolicNode | null>(null);

  // 🖌️ Internal: render trail to canvas
  const renderTrail = (tree: SymbolicNode) => {
    const canvas = canvasRef.current;
    if (!canvas || !tree) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    renderSymbolicTrail({
      context: ctx,
      rootNode: tree,
      currentNodeId: hoveredNodeId, // ✅ highlight hovered node
    });
  };

  // 📡 Fetch tree + render on container change
  useEffect(() => {
    const fetchAndRender = async () => {
      if (!containerId) return;
      try {
        const tree = await fetchHolographicTree(containerId);
        setTreeData(tree.root);
        renderTrail(tree.root);
      } catch (e) {
        console.error('Failed to fetch holographic tree:', e);
      }
    };

    fetchAndRender();
  }, [containerId]);

  // 🖼 Handle canvas resize
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      if (canvas) {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        if (treeData) renderTrail(treeData);
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize();

    return () => window.removeEventListener('resize', handleResize);
  }, [treeData]);

  // 🔁 Re-render when hovered node changes
  useEffect(() => {
    if (treeData) {
      renderTrail(treeData);
    }
  }, [hoveredNodeId]);

  // 🌐 Global API for dynamic overlay triggers
  useEffect(() => {
    (window as any).GHXOverlayRender = (tree: SymbolicNode) => {
      setTreeData(tree);
      renderTrail(tree);
    };

    (window as any).GHXOverlaySetData = (tree: SymbolicNode) => {
      setTreeData(tree);
    };

    (window as any).GHXOverlayFetchAndRender = async (cid: string) => {
      try {
        const tree = await fetchHolographicTree(cid);
        setTreeData(tree.root);
        renderTrail(tree.root);
      } catch (e) {
        console.error('GHXOverlayFetchAndRender failed:', e);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 z-40 pointer-events-none"
      width={1920}
      height={1080}
    />
  );
}