import React, { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";

interface DiffEntry {
  position: string;
  change: "added" | "removed" | "modified";
  glyph?: any;
  from?: any;
  to?: any;
}

export default function MutationDiffViewer() {
  const [diffs, setDiffs] = useState<DiffEntry[]>([]);

  useEffect(() => {
    fetch("/api/aion/memory/mutation-diffs")
      .then((res) => res.json())
      .then((data) => {
        if (data && Array.isArray(data.diffs)) setDiffs(data.diffs);
      })
      .catch((err) => console.error("Failed to load diffs:", err));
  }, []);

  const renderValue = (value: any) =>
    typeof value === "string"
      ? value
      : JSON.stringify(value, null, 2);

  return (
    <Card className="w-full max-h-[600px]">
      <CardContent className="p-2">
        <h2 className="text-lg font-bold mb-2">🧬 Mutation Diffs</h2>
        <ScrollArea className="h-[540px] pr-2">
          {diffs.length === 0 && <p>No mutations detected yet.</p>}
          {diffs.map((diff, idx) => (
            <div
              key={idx}
              className="border-b border-muted py-1 px-1 text-sm space-y-1"
            >
              <div className="flex items-center gap-2">
                <Badge variant="outline">{diff.change.toUpperCase()}</Badge>
                <code>{diff.position}</code>
              </div>
              {diff.change === "modified" && (
                <div>
                  <span className="text-muted-foreground">from:</span>{" "}
                  <code>{renderValue(diff.from)}</code>
                  <span className="ml-2 text-muted-foreground">to:</span>{" "}
                  <code>{renderValue(diff.to)}</code>
                </div>
              )}
              {diff.change !== "modified" && diff.glyph && (
                <div>
                  <span className="text-muted-foreground">glyph:</span>{" "}
                  <code>{renderValue(diff.glyph)}</code>
                </div>
              )}
            </div>
          ))}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}