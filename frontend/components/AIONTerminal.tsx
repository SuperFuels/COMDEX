import React, { useEffect, useState } from 'react';
import axios from 'axios';

type Side = 'left' | 'right';

interface AIONTerminalProps {
  side: Side;
}

const AIONTerminal: React.FC<AIONTerminalProps> = ({ side }) => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<string[]>([]);

  const terminalStyle =
    side === 'left'
      ? 'bg-gray-100 p-4 rounded-md overflow-y-auto h-96'
      : 'bg-gray-100 p-4 rounded-md overflow-y-auto h-96';

  const label = side === 'left' ? 'left' : 'right';

  const print = (text: string) => {
    setMessages((prev) => [...prev, text]);
  };

  const fetchData = async (endpoint: string, label: string) => {
    try {
      const res = await axios.get(`/api/aion/${endpoint}`);
      print(`🧠 AION (${label}):\n${JSON.stringify(res.data, null, 2)}`);
    } catch (err) {
      print(`❌ AION error: ${err}`);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;
    print(`💬 You: ${input}`);
    try {
      const res = await axios.post('/api/aion/prompt', { prompt: input });
      print(`🤖 AION:\n${res.data.response || 'No reply.'}`);
    } catch (err) {
      print(`❌ AION error: ${err}`);
    }
    setInput('');
  };

  // 📦 Listen for footer button events
  useEffect(() => {
    if (side !== 'left') return;

    const listener = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      switch (detail) {
        case 'status':
        case 'goal':
        case 'identity':
        case 'situation':
        case 'boot-skill':
        case 'reflect':
        case 'run-dream':
        case 'game-dream':
          fetchData(detail, detail);
          break;
        default:
          print(`⚠️ Unknown command: ${detail}`);
      }
    };

    window.addEventListener('aion-command', listener);
    return () => window.removeEventListener('aion-command', listener);
  }, [side]);

  return (
    <div className="w-full">
      <div className="text-xs italic text-gray-500 mb-1">Terminal Side: {label}</div>
      <div className="flex space-x-2 mb-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded"
          placeholder="hello aion"
        />
        <button
          onClick={handleSend}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Ask
        </button>
      </div>
      <div className={terminalStyle}>
        {messages.length === 0 ? (
          <p className="text-gray-400">No reply.</p>
        ) : (
          messages.map((msg, i) => (
            <pre key={i} className="whitespace-pre-wrap text-sm mb-2">
              {msg}
            </pre>
          ))
        )}
      </div>
    </div>
  );
};

export default AIONTerminal;