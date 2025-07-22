// 📁 frontend/components/Codex/CodexScrollPresets.tsx

import React from "react";

const presetScrolls: { label: string; code: string }[] = [
  {
    label: "Hello World",
    code: "⊕ greet → user",
  },
  {
    label: "Add Numbers",
    code: "⊕ add → 2 → 3",
  },
  {
    label: "Set Mood",
    code: "⊕ set → emotion → 'hope'",
  },
];

export default function CodexScrollPresets({
  onSelectScroll,
}: {
  onSelectScroll: (code: string) => void;
}) {
  return (
    <div className="space-y-2">
      <h3 className="text-cyan-400 font-semibold">✨ Preset Scrolls</h3>
      <div className="flex flex-wrap gap-2">
        {presetScrolls.map((preset) => (
          <button
            key={preset.label}
            onClick={() => onSelectScroll(preset.code)}
            className="bg-gray-800 hover:bg-gray-700 text-white px-3 py-1 rounded-md border border-cyan-600 text-sm"
          >
            {preset.label}
          </button>
        ))}
      </div>
    </div>
  );
}