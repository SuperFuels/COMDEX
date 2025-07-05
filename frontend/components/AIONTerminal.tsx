import React, { useState } from 'react';

export default function AIONTerminal() {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');
  const [history, setHistory] = useState<string[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    setHistory((prev) => [...prev, `🧠 You: ${input}`]);
    setResponse('⏳ AION is thinking...');

    try {
      const res = await fetch('/api/aion/prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: input }),
      });

      const data = await res.json();
      const reply = data.result || '⚠️ No reply.';
      setHistory((prev) => [...prev, `🤖 AION: ${reply}`]);
    } catch (err) {
      setHistory((prev) => [...prev, '❌ Error communicating with AION.']);
    } finally {
      setInput('');
      setResponse('');
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Main output area */}
      <div className="flex-1 overflow-y-auto p-4 bg-gray-50 text-sm font-mono text-gray-800 space-y-2">
        {history.map((msg, idx) => (
          <div key={idx} className="whitespace-pre-wrap">
            {msg}
          </div>
        ))}
        {response && <div className="text-blue-500">{response}</div>}
      </div>

      {/* Sticky input */}
      <form onSubmit={handleSubmit} className="flex p-2 border-t bg-white">
        <input
          type="text"
          className="flex-1 border rounded px-3 py-2 mr-2 text-sm"
          placeholder="Ask AION something..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button
          type="submit"
          className="bg-blue-500 text-white px-4 py-2 rounded text-sm"
        >
          Ask
        </button>
      </form>
    </div>
  );
}