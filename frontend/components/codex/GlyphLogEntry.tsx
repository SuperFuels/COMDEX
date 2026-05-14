import React from "react";
import { Badge } from "@/components/ui/badge";

interface GlyphLogEntryProps {
  log: any;
  scrolls: Record<string, string>;
  contextShown: Record<string, boolean>;
  toggleContext: (glyph: string) => void;
}

export const GlyphLogEntry: React.FC<GlyphLogEntryProps> = ({
  log,
  scrolls,
  contextShown,
  toggleContext,
}) => {
  const costColor =
    log.cost > 10 ? "text-red-400" : log.cost > 5 ? "text-yellow-400" : "text-green-400";

  return (
    <div className="mb-4 p-2 border border-gray-700 rounded bg-black/40">
      <div className="font-mono text-sm text-green-300">
        ⟦ {log.glyph} ⟧ → <b className="text-purple-400">{log.action}</b>
      </div>

      <div className="flex gap-1 flex-wrap mt-1">
        {log.sqi && <Badge variant="outline">🌌 SQI</Badge>}
        {log.replay_trace && <Badge variant="outline">🛰️ Replay</Badge>}
        {log.entangled_identity && <Badge variant="outline">↔ Identity Link</Badge>}
        {log.trigger_type && <Badge variant="outline">🕒 {log.trigger_type}</Badge>}
        {log.cost !== undefined && (
          <Badge variant="destructive">💰 {log.cost.toFixed(2)}</Badge>
        )}
      </div>

      {log.cost !== undefined && (
        <div className={`text-xs mt-1 ${costColor}`}>
          💰 Estimated Cost: <b>{log.cost.toFixed(2)}</b>
          {log.detail && (
            <div className="flex gap-2 mt-1 flex-wrap">
              {log.detail.energy !== undefined && (
                <Badge variant="outline">🔋 Energy: {log.detail.energy}</Badge>
              )}
              {log.detail.ethics_risk !== undefined && (
                <Badge variant="outline">⚖️ Risk: {log.detail.ethics_risk}</Badge>
              )}
              {log.detail.delay !== undefined && (
                <Badge variant="outline">⌛ Delay: {log.detail.delay}</Badge>
              )}
              {log.detail.opportunity_loss !== undefined && (
                <Badge variant="outline">📉 Loss: {log.detail.opportunity_loss}</Badge>
              )}
              {log.detail.coord && (
                <Badge variant="outline">📍 Coord: {log.detail.coord}</Badge>
              )}
              {log.detail.container && (
                <Badge variant="outline">🧱 Container: {log.detail.container}</Badge>
              )}
              {log.detail.entangled_from && (
                <Badge variant="outline">🪞 Forked from: {log.detail.entangled_from}</Badge>
              )}
              {log.detail.qglyph_id && (
                <Badge variant="outline">🧬 QGlyph ID: {log.detail.qglyph_id}</Badge>
              )}
              {log.detail.qglyph_paths && (
                <Badge variant="outline">
                  ↔ Paths: {log.detail.qglyph_paths[0]} / {log.detail.qglyph_paths[1]}
                </Badge>
              )}
              {log.detail.bias_score !== undefined && (
                <Badge variant="outline">🎯 Bias Score: {log.detail.bias_score}</Badge>
              )}
              {log.detail.observer_trace && (
                <Badge variant="outline">👁️ Trace: {log.detail.observer_trace}</Badge>
              )}
              {log.detail.collapsed_path && (
                <Badge variant="outline">🪞 Forked Path: {log.detail.collapsed_path}</Badge>
              )}
            </div>
          )}
        </div>
      )}

      {scrolls[log.glyph] && (
        <pre className="bg-gray-800 text-green-300 text-xs mt-2 p-2 rounded max-h-40 overflow-auto whitespace-pre-wrap border border-green-800">
          {scrolls[log.glyph]}
        </pre>
      )}

      {contextShown[log.glyph] && log.context && (
        <pre className="bg-gray-900 text-purple-300 text-xs mt-2 p-2 rounded max-h-32 overflow-auto whitespace-pre-wrap border border-purple-800">
          {log.context}
        </pre>
      )}

      {log.context && (
        <div className="text-xs mt-1 text-cyan-300 cursor-pointer hover:underline" onClick={() => toggleContext(log.glyph)}>
          {contextShown[log.glyph] ? '🔽 Hide context' : '🔍 Show context'}
        </div>
      )}
    </div>
  );
};
