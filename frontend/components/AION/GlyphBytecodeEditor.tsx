// File: frontend/components/AION/GlyphBytecodeEditor.tsx

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';

const GlyphBytecodeEditor = () => {
  const [codexLang, setCodexLang] = useState('');
  const [prefix, setPrefix] = useState('⎇:');
  const [coord, setCoord] = useState('0,0,0');
  const [preview, setPreview] = useState('');

  const generateGlyph = () => {
    const encoded = `${prefix}${codexLang.trim()}`;
    setPreview(encoded);
  };

  const handleSave = async () => {
    const res = await fetch('/api/glyph/embed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ coord, glyph: preview })
    });
    if (res.ok) alert('Glyph saved!');
  };

  return (
    <Card className="p-4 w-full">
      <CardContent>
        <h2 className="text-xl mb-2">🧠 Glyph Bytecode Editor</h2>
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <select
              value={prefix}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setPrefix(e.target.value)}
              className="border rounded p-2"
            >
              <option value="⎇:">⎇: Local Exec</option>
              <option value="⧉:">⧉: Remote Glyph</option>
            </select>
            <Input
              value={coord}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCoord(e.target.value)}
              placeholder="x,y,z"
            />
          </div>
          <textarea
            value={codexLang}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCodexLang(e.target.value)}
            rows={4}
            className="border rounded p-2 w-full"
            placeholder="Write CodexLang..."
          />
          <Button onClick={generateGlyph}>Generate Glyph</Button>
          <div className="bg-muted p-2 rounded">
            Preview: <span className="font-mono">{preview}</span>
          </div>
          <Button onClick={handleSave} disabled={!preview}>
            Save to Cube
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default GlyphBytecodeEditor;