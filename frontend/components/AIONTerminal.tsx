import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';

interface AIONTerminalProps {
  side: 'left' | 'right';
}

export default function AIONTerminal({ side }: AIONTerminalProps) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

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
      appendMessage(`❌ Error: ${err?.response?.data?.error || err.message}`);
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
      appendMessage(`✅ ${label}: ${JSON.stringify(res.data, null, 2)}`);
    } catch (err: any) {
      appendMessage(`❌ ${label} error: ${err?.response?.data?.error || err.message}`);
    }
  };

  // Auto-scroll to bottom on new message
  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      <div className="text-xs text-gray-500 italic p-2 border-b bg-white">
        Terminal Side: <strong>{side}</strong>
      </div>

      {/* Input (for right terminal only) */}
      {side === 'right' && (
        <div className="flex px-2 gap-2 mt-2 mb-1">
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
      )}

      {/* Output */}
      <div
        ref={scrollRef}
        className="flex-1 bg-gray-50 p-3 rounded overflow-y-auto text-sm whitespace-pre-wrap border border-gray-300 m-2"
      >
        {messages.length === 0 ? (
          <p className="text-gray-400">No reply yet.</p>
        ) : (
          messages.map((msg, idx) => <div key={idx}>{msg}</div>)
        )}
      </div>

      {/* Action Buttons (left side only) */}
      {side === 'left' && (
        <div className="flex flex-wrap gap-2 px-2 pb-3 text-xs">
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
          <button onClick={() => callEndpoint('/api/aion/skill-reflect', 'Reflect')} className="bg-yellow-500 text-white px-3 py-1 rounded">
            Reflect
          </button>
          <button onClick={() => callEndpoint('/api/aion/run-dream', 'Run Dream')} className="bg-green-600 text-white px-3 py-1 rounded">
            Run Dream
          </button>
          <button onClick={() => callEndpoint('/api/aion/game-dream', 'Game Dream')} className="bg-indigo-600 text-white px-3 py-1 rounded">
            Game Dream
          </button>
          <button disabled className="border border-gray-300 px-3 py-1 rounded text-gray-500 bg-white">
            🌙 Dream Visualizer (coming soon)
          </button>
        </div>
      )}
    </div>
  );
}