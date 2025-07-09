// File: frontend/components/AION/TessarisVisualizer.tsx

import React, { useEffect, useState } from "react";
import { ArrowBigRight } from "lucide-react";
import { cn } from "@/lib/utils";

type BranchNode = {
  id: string;
  symbol: string;
  value?: string;
  children?: BranchNode[];
};

// Fallback Card component
const Card = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={`rounded border bg-white shadow p-4 ${className || ""}`}>
    {children}
  </div>
);

export default function TessarisVisualizer() {
  const [tree, setTree] = useState<BranchNode | null>(null);

  useEffect(() => {
    fetch("/api/aion/tessaris/thought-tree")
      .then((res) => res.json())
      .then((data) => {
        setTree(data?.tree ?? null);
      });
  }, []);

  const renderBranch = (node: BranchNode, depth = 0) => (
    <div className="pl-4 relative mb-2 group" key={node.id}>
      <div className="flex items-center space-x-2">
        <ArrowBigRight
          className={cn(
            "w-4 h-4",
            depth === 0 && "text-green-500",
            depth === 1 && "text-blue-400",
            depth >= 2 && "text-purple-400"
          )}
        />
        <div>
          <span className="font-mono text-sm font-semibold">{node.symbol}</span>
          {node.value && (
            <span className="ml-1 text-muted-foreground text-xs">= {node.value}</span>
          )}
        </div>
      </div>
      {node.children && node.children.length > 0 && (
        <div className="ml-4 border-l border-border pl-4">
          {node.children.map((child) => renderBranch(child, depth + 1))}
        </div>
      )}
    </div>
  );

  return (
    <Card className="max-h-[75vh] overflow-auto">
      <h2 className="text-xl font-bold mb-3">🧠 Tessaris Thought Tree</h2>
      {tree ? (
        renderBranch(tree)
      ) : (
        <p className="text-muted-foreground text-sm">Loading tree...</p>
      )}
    </Card>
  );
}