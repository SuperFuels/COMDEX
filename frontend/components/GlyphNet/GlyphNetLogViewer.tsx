import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { formatDistanceToNow } from "date-fns";
import useWebSocket from "@/hooks/useWebSocket";

type GlyphLogEntry = {
  id: string;
  glyph: string;
  container: string;
  timestamp: string;
  type: string;
  meta?: Record<string, any>;
};

export default function GlyphNetLogViewer() {
  const [log, setLog] = useState<GlyphLogEntry[]>([]);
  const [typeFilter, setTypeFilter] = useState("all");
  const [containerFilter, setContainerFilter] = useState("all");
  const [search, setSearch] = useState("");

  const { emit } = useWebSocket("/ws/glyphnet", () => {
    // Optional: handle incoming WebSocket messages
  });

  useEffect(() => {
    fetch("/api/glyphnet/log")
      .then((res) => res.json())
      .then((data) => setLog(data.entries || []));
  }, []);

  const handleReplay = (entry: GlyphLogEntry) => {
    const replayPacket = {
      type: entry.type,
      glyphs: [{ glyph: entry.glyph }],
      meta: {
        original_id: entry.id,
        replay: true,
        container: entry.container,
      },
    };
    emit("replay", replayPacket);
  };

  const filtered = log.filter((entry) => {
    const typeMatch = typeFilter === "all" || entry.type === typeFilter;
    const containerMatch =
      containerFilter === "all" || entry.container === containerFilter;
    const searchMatch = entry.glyph
      .toLowerCase()
      .includes(search.toLowerCase());
    return typeMatch && containerMatch && searchMatch;
  });

  const uniqueContainers = Array.from(new Set(log.map((e) => e.container)));
  const uniqueTypes = Array.from(new Set(log.map((e) => e.type)));

  return (
    <Card className="w-full h-[600px]">
      <CardContent>
        <h2 className="text-lg font-bold mb-2">📜 GlyphNet Log</h2>
        <div className="flex gap-2 mb-2">
          <Input
            placeholder="Search glyph..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-1/3"
          />
          <Select onValueChange={setTypeFilter}>
            <SelectTrigger className="w-1/3">
              {typeFilter === "all" ? "All Types" : typeFilter}
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {uniqueTypes.map((type) => (
                <SelectItem key={type} value={type}>
                  {type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select onValueChange={setContainerFilter}>
            <SelectTrigger className="w-1/3">
              {containerFilter === "all" ? "All Containers" : containerFilter}
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Containers</SelectItem>
              {uniqueContainers.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <ScrollArea className="h-[500px] pr-2">
          {filtered.map((entry) => (
            <div
              key={entry.id}
              className="flex justify-between items-center mb-2 border-b pb-1"
            >
              <div>
                <div className="font-mono text-md">{entry.glyph}</div>
                <div className="text-xs text-muted-foreground">
                  {entry.type} → {entry.container} •{" "}
                  {formatDistanceToNow(new Date(entry.timestamp), {
                    addSuffix: true,
                  })}
                </div>
              </div>
              <Button
                className="text-sm px-2 py-1 bg-muted hover:bg-muted/80 border"
                onClick={() => handleReplay(entry)}
              >
                Replay
              </Button>
            </div>
          ))}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}