import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface TriggerMapping {
  glyph: string;
  action: string;
  description: string;
}

const defaultTriggers: TriggerMapping[] = [
  { glyph: "🧠", action: "boot_next_skill", description: "Boot next skill" },
  { glyph: "⚙", action: "run_top_goal", description: "Execute top goal" },
  { glyph: "🔬", action: "curiosity_spark", description: "Boost curiosity & humility" },
  { glyph: "🎯", action: "create_reflection_goal", description: "Spawn reflection goal" },
  { glyph: "🌟", action: "unlock_milestone", description: "Unlock milestone" },
  { glyph: "⚛", action: "run_dream", description: "Trigger dream cycle" },
  { glyph: "✦", action: "start_new_milestone", description: "Start milestone manually" },
  { glyph: "🧽", action: "generate_reflection", description: "Trigger reflection engine" },
  { glyph: "⬁", action: "propose_dna_mutation", description: "Propose DNA mutation" },
];

export default function GlyphTriggerEditor() {
  const [triggers, setTriggers] = useState<TriggerMapping[]>(defaultTriggers);
  const [newGlyph, setNewGlyph] = useState("");
  const [newAction, setNewAction] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const addTrigger = () => {
    if (!newGlyph || !newAction) return;
    setTriggers([...triggers, {
      glyph: newGlyph,
      action: newAction,
      description: newDesc,
    }]);
    setNewGlyph("");
    setNewAction("");
    setNewDesc("");
  };

  return (
    <div className="w-80 p-4 space-y-4 border-l bg-gray-50 overflow-y-auto h-full">
      <h2 className="text-lg font-semibold">🧬 Glyph Trigger Editor</h2>

      <div className="space-y-2">
        {triggers.map((trigger, idx) => (
          <Card key={idx} className="bg-white">
            <CardContent className="p-3 space-y-1">
              <div className="text-xl">{trigger.glyph}</div>
              <div className="text-sm text-gray-600">🛠 {trigger.action}</div>
              <div className="text-xs text-gray-400">{trigger.description}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="border-t pt-4 space-y-2">
        <h3 className="text-sm font-medium">➕ Add New Trigger</h3>

        <input
          type="text"
          placeholder="Glyph (e.g. 🪞)"
          value={newGlyph}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewGlyph(e.target.value)}
          className="w-full border rounded px-2 py-1"
        />

        <input
          type="text"
          placeholder="Action name (e.g. reflect_self)"
          value={newAction}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewAction(e.target.value)}
          className="w-full border rounded px-2 py-1"
        />

        <textarea
          placeholder="Description (optional)"
          value={newDesc}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNewDesc(e.target.value)}
          className="w-full border rounded px-2 py-1"
        />

        <Button onClick={addTrigger} className="w-full">
          Add Trigger
        </Button>
      </div>
    </div>
  );
}