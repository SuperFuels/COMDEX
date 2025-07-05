// frontend/components/AIONTerminal.tsx
import React, { useState } from 'react';

export default function AIONTerminal() {
  const [input, setInput] = useState('');
  const [terminalOutput, setTerminalOutput] = useState<string[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const prompt = input;
    setInput('');
    setTerminalOutput(prev => [...prev, `> ${prompt}`, '⌛ Thinking...']);

    try {
      const res = await fetch('/api/aion/prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });

      const data = await res.json();
      const reply = data.result || '🤖 No reply.';
      setTerminalOutput(prev => [...prev.slice(0, -1), `🧠 AION: ${reply}`]);
    } catch (err) {
      setTerminalOutput(prev => [...prev.slice(0, -1), '❌ Error getting reply.']);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 relative">
      {/* Scrollable Output */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2 text-sm font-mono text-gray-800">
        {terminalOutput.map((line, idx) => (
          <div key={idx}>{line}</div>
        ))}
      </div>

      {/* Sticky Input Bar */}
      <form onSubmit={handleSubmit} className="flex-none sticky bottom-0 bg-white border-t p-2 flex items-center gap-2">
        <input
          type="text"
          className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm"
          placeholder="Ask AION anything..."
          value={input}
          onChange={e => setInput(e.target.value)}
        />
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded text-sm">Ask</button>
      </form>
    </div>
  );
}