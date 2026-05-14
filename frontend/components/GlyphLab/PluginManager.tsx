/**
 * 📄 PluginManager.tsx — GlyphLab Plugin Manager UI
 */

"use client";

import React, { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type PluginMeta = {
  name: string;
  version: string;
  purpose: string;
  tags: string[];
  enabled: boolean;
  registered_at: string;
};

export default function PluginManager() {
  const [plugins, setPlugins] = useState<PluginMeta[]>([]);

  const fetchPlugins = async () => {
    try {
      const res = await fetch("/api/aion/plugins");
      const data = await res.json();
      setPlugins(data.plugins || []);
    } catch (err) {
      console.error("Failed to fetch plugins:", err);
    }
  };

  useEffect(() => {
    fetchPlugins();
  }, []);

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-2xl font-bold">🔌 Loaded Glyph Plugins</h2>

      {plugins.map((p) => (
        <Card key={p.name}>
          <CardContent className="p-4">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-xl font-semibold">
                  {p.name}
                  <span className="text-sm text-gray-400 ml-2">v{p.version}</span>
                </h3>
                <p className="text-gray-700">{p.purpose}</p>
                <p className="text-sm text-gray-500 mt-1">
                  🏷️ Tags: <span className="italic">{p.tags.join(", ")}</span>
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  📅 Registered: {p.registered_at}
                </p>
              </div>

              <div className="flex flex-col gap-2">
                {/* No 'variant' prop — style with className */}
                <Button
                  disabled
                  className={
                    p.enabled
                      ? "h-8 px-3 text-sm rounded-md bg-emerald-600/90 text-white cursor-default"
                      : "h-8 px-3 text-sm rounded-md bg-muted text-muted-foreground cursor-not-allowed"
                  }
                >
                  {p.enabled ? "✅ Enabled" : "🚫 Disabled"}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}