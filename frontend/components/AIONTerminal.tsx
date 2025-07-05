import React, { useState } from 'react';
import axios from 'axios';

interface AIONTerminalProps {
  side: 'left' | 'right';
}

export default function AIONTerminal({ side }: AIONTerminalProps) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const appendMessage = (msg: string) => {
    setMessages((prev) => [...prev, msg]);
  };

  const sendPrompt = async () => {
    if (!input.trim()) return;
    appendMessage(`🗨️ You: ${input}`);
    setLoading(true);

    try {
      const res = await axios.post('/api/aion/prompt', { prompt: input });
      appendMessage(`🤖 AION: ${res.data.reply || '(no response)'}`);
    } catch (err: any) {
      appendMessage(`❌ AION error: ${err.message || 'Unknown error'}`);
    }

    setLoading(false);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') sendPrompt();
  };

  const callEndpoint = async (endpoint: string, label: string) => {
    appendMessage(`📡 Fetching ${label}...`);
    try {
      const res = await axios.get(endpoint);
      appendMessage(`✅ ${label}: ${JSON.stringify(res.data)}`);
    } catch (err: any) {
      appendMessage(`❌ ${label} error: ${err.message}`);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Terminal Header */}
      <div className="text-xs text-gray-500 italic p-2">
        Terminal Side: <strong>{side}</strong>
      </div>

      {/* Input Field */}
      <div className="flex px-2 gap-2 mb-2">
        <input
          className="flex-1 border border-gray-300 px-3 py-1 rounded text-sm"
          placeholder="Ask AION something..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          onClick={sendPrompt}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-1 rounded text-sm"
        >
          Ask
        </button>
      </div>

      {/* Output */}
      <div className="flex-1 bg-gray-50 p-3 rounded overflow-y-auto text-sm whitespace-pre-wrap">
        {messages.length === 0 ? (
          <p className="text-gray-400">No reply.</p>
        ) : (
          messages.map((msg, idx) => <div key={idx}>{msg}</div>)
        )}
      </div>

      {/* Inline Actions (optional for side="left" only or both) */}
      {side === 'left' && (
        <div className="mt-2 flex flex-wrap gap-2 p-2 text-xs">
          <button onClick={() => callEndpoint('/api/aion/status', 'Status')} className="bg-blue-600 text-white px-3 py-1 rounded">
            Status
          </button>
          <button onClick={() => callEndpoint('/api/aion/goal', 'Goal')} className="bg-blue-600 text-white px-3 py-1 rounded">
            Goal
          </button>
          <button onClick={() => callEndpoint('/api/aion/identity', 'Identity')} className="bg-blue-600 text-white px-3 py-1 rounded">
            Identity
          </button>
          <button onClick={() => callEndpoint('/api/aion/situation', 'Situation')} className="bg-blue-600 text-white px-3 py-1 rounded">
            Situation
          </button>
          <button onClick={() => callEndpoint('/api/aion/boot-skill', 'Boot Skill')} className="bg-purple-600 text-white px-3 py-1 rounded">
            Boot Skill
          </button>
          <button onClick={() => callEndpoint('/api/aion/skill-reflect', 'Reflect')} className="bg-yellow-400 text-white px-3 py-1 rounded">
            Reflect
          </button>
          <button onClick={() => callEndpoint('/api/aion/run-dream', 'Run Dream')} className="bg-green-600 text-white px-3 py-1 rounded">
            Run Dream
          </button>
          <button onClick={() => callEndpoint('/api/aion/game-dream', 'Game Dream')} className="bg-indigo-600 text-white px-3 py-1 rounded">
            Game Dream
          </button>
          <button disabled className="border border-gray-400 px-3 py-1 rounded text-gray-500">
            Dream Visualizer
          </button>
        </div>
      )}
    </div>
  );
}